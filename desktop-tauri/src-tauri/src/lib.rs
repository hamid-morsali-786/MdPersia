#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod engine;
mod commands;
mod conversion_runtime;
use std::sync::Arc;
use tauri::{Emitter, Manager};
use commands::{Runtime, SharedRuntime, queue_files};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let runtime = Arc::new(Runtime::default());
    queue_files(&runtime, std::env::args().skip(1), &std::env::current_dir().unwrap_or_default());
    let mut builder = tauri::Builder::default().manage(runtime)
        .plugin(tauri_plugin_dialog::init());
    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, argv, cwd| {
            let state = app.state::<SharedRuntime>();
            queue_files(&state, argv.into_iter().skip(1), std::path::Path::new(&cwd));
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize(); let _ = window.show(); let _ = window.set_focus();
            }
            // The event is a notification; the durable queue is drained after subscribing.
            let _ = app.emit("open-files", ());
        }));
    }
    let app = builder.invoke_handler(tauri::generate_handler![
        commands::startup_arguments, commands::preview_html, commands::document_io,
        commands::stat_files, commands::scan_folder, commands::run_conversion,
        commands::cancel_conversion, commands::reveal_path, commands::open_external,
        conversion_runtime::conversion_runtime_status, conversion_runtime::conversion_runtime_install,
        conversion_runtime::conversion_runtime_cancel, conversion_runtime::conversion_runtime_remove,
    ]).build(tauri::generate_context!()).expect("MdPersia could not start");
    app.run(|app, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            let runtime = app.state::<SharedRuntime>();
            runtime.jobs.shutdown(); runtime.engine.shutdown();
            runtime.packages.shutdown();
        }
    });
}
