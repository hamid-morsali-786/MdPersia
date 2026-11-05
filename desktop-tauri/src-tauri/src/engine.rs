use std::{collections::HashMap, io::{BufRead, BufReader, Read, Write}, path::PathBuf,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio}, sync::Mutex};
use serde_json::{json, Value};
use tauri::{AppHandle, Manager};

/// A kill-on-close Windows Job owns every engine descendant, including Chromium.
/// Closing the application or cancelling a conversion cannot leave browser workers behind.
pub struct ProcessTree {
    #[cfg(windows)]
    handle: windows_sys::Win32::Foundation::HANDLE,
}
#[cfg(windows)]
unsafe impl Send for ProcessTree {}

impl ProcessTree {
    pub fn attach(child: &mut Child) -> Result<Self, String> {
        #[cfg(windows)]
        unsafe {
            use std::os::windows::io::AsRawHandle;
            use windows_sys::Win32::{Foundation::CloseHandle, System::JobObjects::*};
            let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
            if handle.is_null() { let _ = child.kill(); return Err(std::io::Error::last_os_error().to_string()); }
            let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if SetInformationJobObject(handle, JobObjectExtendedLimitInformation,
                &limits as *const _ as *const _, std::mem::size_of_val(&limits) as u32) == 0
                || AssignProcessToJobObject(handle, child.as_raw_handle() as _) == 0 {
                let error = std::io::Error::last_os_error().to_string();
                let _ = child.kill(); CloseHandle(handle); return Err(error);
            }
            Ok(Self { handle })
        }
        #[cfg(not(windows))]
        { let _ = child; Ok(Self {}) }
    }

    pub fn terminate(&self, child: &mut Child) {
        #[cfg(windows)]
        unsafe { windows_sys::Win32::System::JobObjects::TerminateJobObject(self.handle, 1); }
        let _ = child.kill();
    }
}
impl Drop for ProcessTree {
    fn drop(&mut self) {
        #[cfg(windows)]
        unsafe { windows_sys::Win32::Foundation::CloseHandle(self.handle); }
    }
}

pub struct Layout { pub executable: PathBuf, pub prefix: Vec<String>, pub assets: PathBuf, pub bundled: bool }
impl Layout {
    pub fn resolve(app: &AppHandle) -> Result<Self, String> {
        let resources = app.path().resource_dir().map_err(|e| e.to_string())?;
        let executable = resources.join("reader").join(if cfg!(windows) { "mdpersia-reader.exe" } else { "mdpersia-reader" });
        if executable.is_file() {
            return Ok(Self { executable, prefix: vec![], assets: resources.join("assets"), bundled: true });
        }
        #[cfg(debug_assertions)]
        {
            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().map_err(|e| e.to_string())?;
            return Ok(Self { executable: std::env::var("PYTHON_EXECUTABLE").unwrap_or_else(|_| "python".into()).into(),
                prefix: vec!["-u".into(), "-m".into(), "fa_md_pdf.desktop_engine".into()], assets: root, bundled: false });
        }
        #[cfg(not(debug_assertions))]
        Err("موتور داخلی MdPersia پیدا نشد؛ برنامه را دوباره نصب کنید.".into())
    }

    pub fn conversion(app: &AppHandle) -> Result<Self, String> {
        #[cfg(debug_assertions)]
        if !app.path().resource_dir().map_err(|e| e.to_string())?.join("reader/mdpersia-reader.exe").is_file() {
            return Self::resolve(app);
        }
        let root = crate::conversion_runtime::installed_dir(app)?;
        Ok(Self { executable: root.join("engine/mdpersia-engine.exe"), prefix: vec![],
            assets: root.join("assets"), bundled: true })
    }

    pub fn command(&self, mode: &str) -> Command {
        let mut cmd = Command::new(&self.executable);
        #[cfg(windows)]
        { use std::os::windows::process::CommandExt; cmd.creation_flags(0x08000000); }
        cmd.args(&self.prefix).arg("--assets-dir").arg(&self.assets).arg(mode)
            .current_dir(&self.assets).env_remove("PYTHONHOME").env_remove("PYTHONPATH")
            .env("PYTHONIOENCODING", "utf-8").env("PYTHONUTF8", "1").env("PYTHONUNBUFFERED", "1")
            .env("PYTHONNOUSERSITE", "1");
        if !self.bundled { cmd.env("PYTHONPATH", self.assets.join("src")); }
        cmd
    }
}

struct Worker { child: Child, tree: ProcessTree, input: ChildStdin, output: BufReader<ChildStdout>, sequence: u64 }
impl Worker {
    fn start(app: &AppHandle) -> Result<Self, String> {
        let layout = Layout::resolve(app)?;
        let log_dir = app.path().app_log_dir().map_err(|e| e.to_string())?;
        std::fs::create_dir_all(&log_dir).map_err(|e| e.to_string())?;
        let log = std::fs::OpenOptions::new().create(true).append(true).open(log_dir.join("engine.log")).map_err(|e| e.to_string())?;
        let mut child = layout.command("--worker").stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(log).spawn().map_err(|e| e.to_string())?;
        let tree = ProcessTree::attach(&mut child)?;
        let input = child.stdin.take().ok_or("Engine input unavailable")?;
        let output = BufReader::new(child.stdout.take().ok_or("Engine output unavailable")?);
        Ok(Self { child, tree, input, output, sequence: 0 })
    }
    fn request(&mut self, mut request: Value) -> Result<Value, String> {
        self.sequence += 1;
        request["id"] = json!(self.sequence);
        serde_json::to_writer(&mut self.input, &request).map_err(|e| e.to_string())?;
        self.input.write_all(b"\n").and_then(|_| self.input.flush()).map_err(|e| e.to_string())?;
        let mut response = String::new();
        Read::by_ref(&mut self.output).take(64 * 1024 * 1024).read_line(&mut response).map_err(|e| e.to_string())?;
        if !response.ends_with('\n') { return Err("پاسخ موتور کامل دریافت نشد؛ فایل را بازخوانی کنید.".into()); }
        let value: Value = serde_json::from_str(&response).map_err(|e| e.to_string())?;
        if value["id"] != request["id"] { return Err("پاسخ نامعتبر از موتور داخلی دریافت شد.".into()); }
        Ok(value)
    }
}
impl Drop for Worker {
    fn drop(&mut self) { self.tree.terminate(&mut self.child); let _ = self.child.wait(); }
}

#[derive(Default)]
pub struct Engine { worker: Mutex<Option<Worker>> }
impl Engine {
    pub fn request(&self, app: &AppHandle, request: Value) -> Result<Value, String> {
        let mut worker = self.worker.lock().map_err(|_| "Engine lock unavailable")?;
        if worker.is_none() { *worker = Some(Worker::start(app)?); }
        let result = worker.as_mut().unwrap().request(request);
        // Never replay a write after a lost response. A fresh explicit read determines its outcome.
        if result.is_err() { *worker = None; }
        result
    }
    pub fn shutdown(&self) { if let Ok(mut worker) = self.worker.try_lock() { *worker = None; } }
}

pub struct Job { pub child: Option<Child>, pub tree: Option<ProcessTree>, pub cancelled: bool }
#[derive(Default)]
pub struct Jobs { pub entries: Mutex<HashMap<String, Job>> }
impl Jobs {
    pub fn cancel(&self, id: &str) -> Result<(), String> {
        let mut entries = self.entries.lock().map_err(|_| "Job lock unavailable")?;
        if let Some(job) = entries.get_mut(id) {
            job.cancelled = true;
            if let (Some(child), Some(tree)) = (&mut job.child, &job.tree) { tree.terminate(child); }
        }
        Ok(())
    }
    pub fn shutdown(&self) {
        if let Ok(mut entries) = self.entries.lock() {
            for job in entries.values_mut() {
                if let (Some(child), Some(tree)) = (&mut job.child, &job.tree) { tree.terminate(child); }
            }
            entries.clear();
        }
    }
}
