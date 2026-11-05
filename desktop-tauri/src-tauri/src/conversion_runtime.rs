//! Explicit, integrity-checked installation of the optional conversion engine.
use std::{fs::{self, File}, future::Future, io::{Read, Write}, path::{Component, Path, PathBuf},
    sync::{Mutex, atomic::{AtomicBool, Ordering}}, time::{Duration, Instant, SystemTime, UNIX_EPOCH}};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Emitter, Manager as TauriManager, State};
use crate::{commands::SharedRuntime, engine::{Layout, ProcessTree}};

const CATALOG: &str = include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../output/release/staging/conversion-catalog.json"));
const CANCELLED: &str = "download_cancelled";

#[derive(Clone, Deserialize)]
#[serde(rename_all="camelCase")]
pub struct Catalog {
    pub version: String, pub sha256: String, pub bytes: u64, pub filename: String,
    pub url: String, pub engine_version: String, pub browser_executable: String,
}
fn catalog() -> Result<Catalog, String> {
    let value: Catalog = serde_json::from_str(CATALOG).map_err(|e| e.to_string())?;
    if value.version != env!("CARGO_PKG_VERSION") || value.sha256.len() != 64
        || !value.sha256.bytes().all(|b| b.is_ascii_hexdigit())
        || !value.url.starts_with("https://github.com/") || value.bytes == 0 {
        return Err("اطلاعات بستهٔ تبدیل با این نسخهٔ برنامه سازگار نیست.".into());
    }
    Ok(value)
}
fn cache_root(app: &AppHandle) -> Result<PathBuf, String> {
    Ok(app.path().app_local_data_dir().map_err(|e| e.to_string())?.join("conversion-runtime"))
}
fn target(app: &AppHandle, info: &Catalog) -> Result<PathBuf, String> {
    Ok(cache_root(app)?.join(&info.sha256))
}
fn valid_install(path: &Path, info: &Catalog) -> bool {
    let receipt = fs::read(path.join("installed.json")).ok()
        .and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok());
    receipt.is_some_and(|r| r["sha256"] == info.sha256)
        && path.join("engine/mdpersia-engine.exe").is_file()
        && path.join(&info.browser_executable).is_file()
        && path.join("assets/vendor/mermaid.min.js").is_file()
        && path.join("assets/fonts/Vazirmatn-Regular.ttf").is_file()
}
pub fn installed_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let info = catalog()?;
    let directory = target(app, &info)?;
    if !valid_install(&directory, &info) {
        return Err("برای خروجی PDF یا Word، موتور تبدیل را از تنظیمات دریافت کنید.".into());
    }
    Ok(directory)
}

#[derive(Clone, Default)]
struct Transfer { phase: String, received: u64, error: Option<String> }
#[derive(Clone, Serialize)]
#[serde(rename_all="camelCase")]
pub struct RuntimeInfo {
    installed: bool, phase: String, downloaded_bytes: u64, total_bytes: u64,
    version: String, download_url: String, sha256: String, directory: String, error: Option<String>,
}
#[derive(Default)]
pub struct PackageManager { active: AtomicBool, cancelled: AtomicBool, transfer: Mutex<Transfer> }
struct Active<'a>(&'a AtomicBool);
impl Drop for Active<'_> { fn drop(&mut self) { self.0.store(false, Ordering::SeqCst); } }

impl PackageManager {
    pub fn info(&self, app: &AppHandle) -> Result<RuntimeInfo, String> {
        let info = catalog()?;
        let directory = target(app, &info)?;
        let installed = valid_install(&directory, &info);
        let transfer = self.transfer.lock().map_err(|_| "Download state unavailable")?.clone();
        let phase = if installed && !self.active.load(Ordering::SeqCst) { "ready".into() }
            else if transfer.phase.is_empty() { "idle".into() } else { transfer.phase };
        Ok(RuntimeInfo { installed, phase, downloaded_bytes: transfer.received,
            total_bytes: info.bytes, version: info.version, download_url: info.url,
            sha256: info.sha256, directory: directory.to_string_lossy().into(), error: transfer.error })
    }
    fn update(&self, app: &AppHandle, phase: &str, received: u64, error: Option<String>) {
        if let Ok(mut state) = self.transfer.lock() { *state = Transfer { phase: phase.into(), received, error }; }
        if let Ok(info) = self.info(app) { let _ = app.emit("conversion-runtime-progress", info); }
    }
    fn check_cancel(&self) -> Result<(), String> {
        if self.cancelled.load(Ordering::SeqCst) { Err(CANCELLED.into()) } else { Ok(()) }
    }
    pub fn cancel(&self, app: &AppHandle) -> Result<RuntimeInfo, String> {
        let info = self.info(app)?;
        if self.active.load(Ordering::SeqCst) && !info.installed {
            self.cancelled.store(true, Ordering::SeqCst);
            self.update(app, "cancelling", info.downloaded_bytes, None);
        }
        self.info(app)
    }
    pub fn shutdown(&self) { self.cancelled.store(true, Ordering::SeqCst); }

    pub fn install(&self, app: &AppHandle, source: Option<String>) -> Result<RuntimeInfo, String> {
        let info = catalog()?;
        let destination = target(app, &info)?;
        if valid_install(&destination, &info) { return self.info(app); }
        if self.active.compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst).is_err() {
            return Err("دریافت دیگری هنوز در حال انجام است.".into());
        }
        let _active = Active(&self.active);
        self.cancelled.store(false, Ordering::SeqCst);
        let root = cache_root(app)?;
        fs::create_dir_all(&root).map_err(|e| e.to_string())?;
        // Only this manager's abandoned temporary folders, never documents or profiles.
        for entry in fs::read_dir(&root).map_err(|e| e.to_string())?.flatten() {
            if entry.file_name().to_string_lossy().starts_with(".download-") {
                let _ = remove_owned(&root, &entry.path());
            }
        }
        let nonce = SystemTime::now().duration_since(UNIX_EPOCH).map_err(|e| e.to_string())?.as_nanos();
        let temporary = root.join(format!(".download-{nonce}"));
        fs::create_dir(&temporary).map_err(|e| e.to_string())?;
        let result = (|| {
            let archive = temporary.join("payload.zip");
            let phase = if source.is_some() { "copying" } else { "downloading" };
            self.update(app, phase, 0, None);
            let mut output = File::create(&archive).map_err(|e| e.to_string())?;
            let mut hash = Sha256::new();
            let mut received = 0u64;
            let mut last = Instant::now();
            let mut accept = |chunk: &[u8]| -> Result<(), String> {
                self.check_cancel()?;
                received = received.checked_add(chunk.len() as u64).ok_or("حجم بسته معتبر نیست.")?;
                if received > info.bytes { return Err("حجم بسته با نسخهٔ برنامه سازگار نیست.".into()); }
                output.write_all(chunk).map_err(|e| e.to_string())?;
                hash.update(chunk);
                if last.elapsed() >= Duration::from_millis(200) {
                    self.update(app, phase, received, None); last = Instant::now();
                }
                Ok(())
            };
            if let Some(path) = source {
                let mut file = File::open(path).map_err(|e| e.to_string())?;
                if file.metadata().map_err(|e| e.to_string())?.len() != info.bytes {
                    return Err("این فایل، بستهٔ تبدیل همین نسخهٔ MdPersia نیست.".into());
                }
                let mut buffer = [0u8; 64 * 1024];
                loop { let count = file.read(&mut buffer).map_err(|e| e.to_string())?;
                    if count == 0 { break; } accept(&buffer[..count])?; }
            } else {
                tauri::async_runtime::block_on(async {
                    let client = reqwest::Client::builder().connect_timeout(Duration::from_secs(15))
                        .read_timeout(Duration::from_secs(30)).timeout(Duration::from_secs(7200))
                        .redirect(reqwest::redirect::Policy::limited(10))
                        .user_agent(concat!("MdPersia/", env!("CARGO_PKG_VERSION"))).build()
                        .map_err(|_| "ارتباط امن برای دریافت بسته آماده نشد.")?;
                    let response = cancellable(&self.cancelled, client.get(&info.url).send()).await?;
                    let mut response = response.map_err(|_| "دریافت از سرور انجام نشد؛ اتصال اینترنت را بررسی کنید یا از فایل ZIP نصب کنید.")?;
                    if !response.status().is_success() || response.url().scheme() != "https" {
                        return Err(format!("سرور دریافت پاسخ معتبر نداد (HTTP {}).", response.status().as_u16()));
                    }
                    loop {
                        let chunk = cancellable(&self.cancelled, response.chunk()).await?
                            .map_err(|_| "ارتباط دریافت قطع شد؛ دوباره تلاش کنید یا از فایل ZIP نصب کنید.")?;
                        match chunk { Some(bytes) => accept(&bytes)?, None => break }
                    }
                    Ok::<(), String>(())
                })?;
            }
            drop(accept);
            output.sync_all().map_err(|e| e.to_string())?;
            drop(output);
            self.check_cancel()?;
            self.update(app, "verifying", received, None);
            if received != info.bytes || format!("{:x}", hash.finalize()) != info.sha256 {
                return Err("فایل دریافت‌شده سالم یا مربوط به این نسخه نیست؛ نصب انجام نشد. دوباره دریافت کنید.".into());
            }
            self.update(app, "installing", received, None);
            let content = temporary.join("content");
            fs::create_dir(&content).map_err(|e| e.to_string())?;
            extract(&archive, &content, &self.cancelled)?;
            self.check_cancel()?;
            let layout = Layout { executable: content.join("engine/mdpersia-engine.exe"),
                prefix: vec![], assets: content.join("assets"), bundled: true };
            let mut child = layout.command("--doctor").stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped()).spawn().map_err(|e| e.to_string())?;
            let _tree = ProcessTree::attach(&mut child)?;
            let output = child.wait_with_output().map_err(|e| e.to_string())?;
            let doctor: serde_json::Value = serde_json::from_slice(&output.stdout).map_err(|_| "موتور تبدیل قابل اجرا نیست؛ بسته را دوباره دریافت کنید.")?;
            if !output.status.success() || doctor["version"] != info.engine_version
                || doctor["browserPresent"] != true || doctor["fontPresent"] != true {
                return Err("بررسی موتور تبدیل کامل نشد؛ نصب قبلی حفظ شد.".into());
            }
            self.check_cancel()?;
            fs::write(content.join("installed.json"), serde_json::to_vec(&serde_json::json!({
                "sha256": info.sha256, "version": info.version })).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
            let backup = root.join(format!(".old-{nonce}"));
            if destination.exists() { fs::rename(&destination, &backup).map_err(|e| e.to_string())?; }
            if let Err(error) = fs::rename(&content, &destination) {
                if backup.exists() { let _ = fs::rename(&backup, &destination); }
                return Err(error.to_string());
            }
            let _ = remove_owned(&root, &backup);
            self.update(app, "ready", info.bytes, None);
            self.info(app)
        })();
        let _ = remove_owned(&root, &temporary);
        if let Err(ref error) = result {
            let cancelled = error == CANCELLED;
            self.update(app, if cancelled { "cancelled" } else { "error" }, 0,
                if cancelled { None } else { Some(error.clone()) });
        }
        result.map_err(|e| if e == CANCELLED { "دریافت موتور متوقف شد.".into() } else { e })
    }
    pub fn remove(&self, app: &AppHandle) -> Result<RuntimeInfo, String> {
        if self.active.compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst).is_err() {
            return Err("ابتدا دریافت جاری را متوقف کنید.".into());
        }
        let _active = Active(&self.active);
        let info = catalog()?;
        remove_owned(&cache_root(app)?, &target(app, &info)?)?;
        self.update(app, "idle", 0, None);
        self.info(app)
    }
}

async fn cancellable<F: Future>(cancelled: &AtomicBool, future: F) -> Result<F::Output, String> {
    let mut future = Box::pin(future);
    loop {
        if cancelled.load(Ordering::SeqCst) { return Err(CANCELLED.into()); }
        if let Ok(value) = tokio::time::timeout(Duration::from_millis(200), &mut future).await { return Ok(value); }
    }
}
fn remove_owned(root: &Path, path: &Path) -> Result<(), String> {
    if path.parent() != Some(root) { return Err("مسیر پاک‌سازی بسته معتبر نیست.".into()); }
    if path.exists() { fs::remove_dir_all(path).map_err(|e| e.to_string())?; }
    Ok(())
}
fn member_path(name: &str) -> Result<PathBuf, String> {
    if name.is_empty() || name.chars().any(|c| matches!(c, '\\' | ':' | '\0'))
        || name.split('/').any(|p| p.is_empty() || p == "." || p == "..") {
        return Err("مسیر نامعتبر در بستهٔ تبدیل پیدا شد.".into());
    }
    let path = PathBuf::from(name);
    if path.components().any(|p| !matches!(p, Component::Normal(_))) {
        return Err("مسیر نامعتبر در بستهٔ تبدیل پیدا شد.".into());
    }
    Ok(path)
}
fn extract(archive: &Path, root: &Path, cancelled: &AtomicBool) -> Result<(), String> {
    let mut archive = zip::ZipArchive::new(File::open(archive).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    if archive.len() > 5000 { return Err("تعداد فایل‌های بسته معتبر نیست.".into()); }
    let mut total = 0u64;
    for index in 0..archive.len() {
        if cancelled.load(Ordering::SeqCst) { return Err(CANCELLED.into()); }
        let mut entry = archive.by_index(index).map_err(|e| e.to_string())?;
        let relative = member_path(entry.name().trim_end_matches('/'))?;
        if entry.unix_mode().is_some_and(|mode| mode & 0o170000 == 0o120000) { return Err("پیوند در بسته مجاز نیست.".into()); }
        let output = root.join(relative);
        if entry.is_dir() { fs::create_dir_all(output).map_err(|e| e.to_string())?; continue; }
        let expected = entry.size();
        if expected > 512 * 1024 * 1024 { return Err("حجم فایل بسته معتبر نیست.".into()); }
        total = total.checked_add(expected).ok_or("حجم بسته معتبر نیست.")?;
        if total > 1024 * 1024 * 1024 { return Err("حجم بازشدهٔ بسته معتبر نیست.".into()); }
        if let Some(parent) = output.parent() { fs::create_dir_all(parent).map_err(|e| e.to_string())?; }
        let mut file = File::options().write(true).create_new(true).open(output).map_err(|e| e.to_string())?;
        let copied = std::io::copy(&mut (&mut entry).take(expected + 1), &mut file).map_err(|e| e.to_string())?;
        if copied != expected { return Err("فایل ناقص در بسته پیدا شد.".into()); }
    }
    Ok(())
}

#[tauri::command]
pub fn conversion_runtime_status(app: AppHandle, runtime: State<'_, SharedRuntime>) -> Result<RuntimeInfo, String> { runtime.packages.info(&app) }
#[tauri::command]
pub async fn conversion_runtime_install(app: AppHandle, runtime: State<'_, SharedRuntime>, source_path: Option<String>) -> Result<RuntimeInfo, String> {
    let runtime = runtime.inner().clone();
    tauri::async_runtime::spawn_blocking(move || runtime.packages.install(&app, source_path)).await.map_err(|e| e.to_string())?
}
#[tauri::command]
pub fn conversion_runtime_cancel(app: AppHandle, runtime: State<'_, SharedRuntime>) -> Result<RuntimeInfo, String> { runtime.packages.cancel(&app) }
#[tauri::command]
pub async fn conversion_runtime_remove(app: AppHandle, runtime: State<'_, SharedRuntime>) -> Result<RuntimeInfo, String> {
    let runtime = runtime.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let jobs = runtime.jobs.entries.lock().map_err(|_| "Job lock unavailable")?;
        if !jobs.is_empty() { return Err("حذف موتور پس از پایان تبدیل یا توقف پایش ممکن است.".into()); }
        runtime.packages.remove(&app)
    }).await.map_err(|e| e.to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_archive_paths_that_can_escape_or_reinterpret_the_target() {
        for name in ["../escape", "/absolute", "C:/escape", "a/../escape", "a\\b", "a//b", "./file"] {
            assert!(member_path(name).is_err(), "{name}");
        }
        assert_eq!(member_path("engine/_internal/python311.dll").unwrap(), PathBuf::from("engine/_internal/python311.dll"));
    }
    #[test]
    fn catalog_matches_the_running_application_and_has_a_pinned_hash() { assert!(catalog().is_ok()); }
}
