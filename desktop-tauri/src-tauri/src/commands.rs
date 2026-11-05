use std::{io::{BufRead, BufReader}, path::{Path, PathBuf}, process::Stdio, sync::{Arc, Mutex}, time::Duration};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{ipc::Channel, AppHandle, Manager, State};
use crate::engine::{Engine, Job, Jobs, Layout, ProcessTree};

#[derive(Default)]
pub struct Runtime { pub engine: Engine, pub jobs: Jobs, pub pending: Mutex<Vec<String>>, pub packages: crate::conversion_runtime::PackageManager }
pub type SharedRuntime = Arc<Runtime>;

pub fn is_markdown(path: &Path) -> bool {
    path.extension().and_then(|e| e.to_str()).is_some_and(|e| e.eq_ignore_ascii_case("md") || e.eq_ignore_ascii_case("markdown"))
}

pub fn queue_files(runtime: &Runtime, args: impl Iterator<Item=String>, cwd: &Path) {
    if let Ok(mut pending) = runtime.pending.lock() {
        for arg in args {
            let path = PathBuf::from(arg);
            let path = if path.is_absolute() { path } else { cwd.join(path) };
            if is_markdown(&path) && path.is_file() {
                let path = path.to_string_lossy().into_owned();
                if !pending.iter().any(|old| old.eq_ignore_ascii_case(&path)) { pending.push(path); }
            }
        }
    }
}

#[tauri::command]
pub fn startup_arguments(runtime: State<'_, SharedRuntime>) -> Result<Vec<String>, String> {
    Ok(std::mem::take(&mut *runtime.pending.lock().map_err(|_| "Open-file queue unavailable")?))
}

#[derive(Deserialize)]
pub struct PreviewRequest { path: String, text: Option<String> }

#[tauri::command]
pub async fn preview_html(app: AppHandle, runtime: State<'_, SharedRuntime>, request: PreviewRequest) -> Result<Value, String> {
    let runtime = runtime.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let source = Path::new(&request.path);
        if !is_markdown(source) || !source.is_file() { return Err("یک فایل Markdown موجود انتخاب کنید.".into()); }
        if let Some(parent) = source.parent() { app.asset_protocol_scope().allow_directory(parent, true).map_err(|e| e.to_string())?; }
        let result = runtime.engine.request(&app, json!({"operation":"preview", "path":request.path, "text":request.text}))?;
        if result["html"].is_string() { Ok(result) } else { Err(result["error"].as_str().unwrap_or("پیش‌نمایش ساخته نشد.").to_owned()) }
    }).await.map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn document_io(app: AppHandle, runtime: State<'_, SharedRuntime>, request: Value) -> Result<Value, String> {
    if !matches!(request["operation"].as_str(), Some("read" | "save")) { return Err("عملیات سند معتبر نیست.".into()); }
    let runtime = runtime.inner().clone();
    tauri::async_runtime::spawn_blocking(move || runtime.engine.request(&app, request)).await.map_err(|e| e.to_string())?
}

#[derive(Serialize)]
#[serde(rename_all="camelCase")]
pub struct FileInfo { path: String, name: String, size_bytes: u64, size_str: String, relative_path: String }
fn file_info(path: &Path, root: &Path) -> Result<FileInfo, String> {
    let metadata = path.metadata().map_err(|e| e.to_string())?;
    if !metadata.is_file() { return Err("مسیر انتخاب‌شده فایل نیست.".into()); }
    Ok(FileInfo { path: path.to_string_lossy().replace('\\', "/"), name: path.file_name().unwrap_or_default().to_string_lossy().into(),
        size_bytes: metadata.len(), size_str: format!("{:.1} KB", metadata.len() as f64 / 1024.0),
        relative_path: path.strip_prefix(root).unwrap_or(path).to_string_lossy().replace('\\', "/") })
}

#[tauri::command]
pub async fn stat_files(paths: Vec<String>) -> Result<Vec<FileInfo>, String> {
    if paths.len() > 10000 { return Err("تعداد فایل‌های انتخاب‌شده بیش از حد است.".into()); }
    tauri::async_runtime::spawn_blocking(move || paths.iter().map(|p| file_info(Path::new(p), Path::new(p).parent().unwrap_or(Path::new("")))).collect()).await.map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn scan_folder(folder_path: String, recursive: bool) -> Result<Vec<FileInfo>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        fn visit(root: &Path, dir: &Path, recursive: bool, files: &mut Vec<FileInfo>) -> Result<(), String> {
            for entry in dir.read_dir().map_err(|e| e.to_string())? {
                let entry = entry.map_err(|e| e.to_string())?;
                let kind = entry.file_type().map_err(|e| e.to_string())?;
                if kind.is_symlink() { continue; }
                if kind.is_dir() && recursive { visit(root, &entry.path(), true, files)?; }
                else if kind.is_file() && is_markdown(&entry.path()) { files.push(file_info(&entry.path(), root)?); }
            }
            Ok(())
        }
        let root = Path::new(&folder_path);
        if !root.is_dir() { return Err("پوشه پیدا نشد یا قابل دسترسی نیست.".into()); }
        let mut files = vec![];
        visit(root, root, recursive, &mut files)?;
        files.sort_by(|a,b| a.path.cmp(&b.path));
        Ok(files)
    }).await.map_err(|e| e.to_string())?
}

#[derive(Clone, Serialize)]
#[serde(tag="type", rename_all="lowercase")]
pub enum ProcessEvent { Stdout { text: String }, Stderr { text: String } }

#[tauri::command]
pub async fn run_conversion(app: AppHandle, runtime: State<'_, SharedRuntime>, id: String, args: Vec<String>, events: Channel<ProcessEvent>) -> Result<i32, String> {
    if id.len() > 128 || args.is_empty() || args.len() > 256 || args.iter().any(|a| a.len() > 32768 || a.contains('\0'))
        || !is_markdown(Path::new(&args[0])) || args.iter().any(|a| matches!(a.as_str(), "--gui" | "--register-associations" | "--unregister-associations" | "--association-status")) {
        return Err("درخواست تبدیل معتبر نیست.".into());
    }
    let runtime = runtime.inner().clone();
    {
        let mut jobs = runtime.jobs.entries.lock().map_err(|_| "Job lock unavailable")?;
        if !jobs.is_empty() { return Err("تبدیل دیگری هنوز در حال اجراست.".into()); }
        jobs.insert(id.clone(), Job { child: None, tree: None, cancelled: false });
    }
    tauri::async_runtime::spawn_blocking(move || {
        let result = (|| {
            let layout = if args.iter().any(|a| a == "--wrap-rtl") { Layout::resolve(&app)? } else { Layout::conversion(&app)? };
            let mut child = layout.command("--convert").args(args).stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().map_err(|e| e.to_string())?;
            let tree = ProcessTree::attach(&mut child)?;
            let stdout = child.stdout.take().ok_or("Engine stdout unavailable")?;
            let stderr = child.stderr.take().ok_or("Engine stderr unavailable")?;
            let out_events = events.clone();
            let output = std::thread::spawn(move || { for text in BufReader::new(stdout).lines().map_while(Result::ok) { let _ = out_events.send(ProcessEvent::Stdout { text: text + "\n" }); } });
            let errors = std::thread::spawn(move || { for text in BufReader::new(stderr).lines().map_while(Result::ok) { let _ = events.send(ProcessEvent::Stderr { text: text + "\n" }); } });
            {
                let mut jobs = runtime.jobs.entries.lock().map_err(|_| "Job lock unavailable")?;
                let slot = jobs.get_mut(&id).ok_or("Conversion cancelled")?;
                if slot.cancelled { tree.terminate(&mut child); }
                slot.child = Some(child); slot.tree = Some(tree);
            }
            let code = loop {
                let status = {
                    let mut jobs = runtime.jobs.entries.lock().map_err(|_| "Job lock unavailable")?;
                    jobs.get_mut(&id).and_then(|job| job.child.as_mut()).ok_or("Conversion stopped")?.try_wait().map_err(|e| e.to_string())?
                };
                if let Some(status) = status { break status.code().unwrap_or(1); }
                std::thread::sleep(Duration::from_millis(30));
            };
            runtime.jobs.entries.lock().map_err(|_| "Job lock unavailable")?.remove(&id);
            let _ = output.join(); let _ = errors.join();
            Ok(code)
        })();
        if let Ok(mut jobs) = runtime.jobs.entries.lock() { jobs.remove(&id); }
        result
    }).await.map_err(|e| e.to_string())?
}

#[tauri::command]
pub fn cancel_conversion(runtime: State<'_, SharedRuntime>, id: String) -> Result<(), String> { runtime.jobs.cancel(&id) }

#[tauri::command]
pub async fn open_external(url: String) -> Result<(), String> {
    let parsed = url::Url::parse(&url).map_err(|e| e.to_string())?;
    if !matches!(parsed.scheme(), "http" | "https") { return Err("فقط پیوند وب قابل بازشدن است.".into()); }
    open::that_detached(url).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn reveal_path(target_path: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let path = PathBuf::from(target_path);
        if !path.exists() { return Err("مسیر انتخاب‌شده پیدا نشد.".into()); }
        #[cfg(windows)]
        if path.is_file() {
            use std::os::windows::ffi::OsStrExt;
            use windows_sys::Win32::{System::Com::*, UI::Shell::*};
            let path: Vec<u16> = path.as_os_str().encode_wide().chain(Some(0)).collect();
            unsafe {
                let initialized = CoInitializeEx(std::ptr::null(), COINIT_APARTMENTTHREADED as u32) >= 0;
                let pidl = ILCreateFromPathW(path.as_ptr());
                let result = if pidl.is_null() { -1 } else { let result = SHOpenFolderAndSelectItems(pidl, 0, std::ptr::null(), 0); ILFree(pidl); result };
                if initialized { CoUninitialize(); }
                return if result >= 0 { Ok(()) } else { Err("بازکردن محل فایل انجام نشد.".into()) };
            }
        }
        open::that_detached(path).map_err(|e| e.to_string())
    }).await.map_err(|e| e.to_string())?
}
