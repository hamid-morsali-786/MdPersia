fn main() {
    let manifest_dir = std::path::PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let staging = manifest_dir.join("../../output/release/staging");
    if !staging.join("conversion-catalog.json").exists() {
        let _ = std::fs::create_dir_all(staging.join("assets"));
        let _ = std::fs::create_dir_all(staging.join("reader"));
        let catalog = format!(
            r#"{{
  "version": "{}",
  "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "bytes": 1,
  "filename": "dev-placeholder.zip",
  "engineVersion": "dev",
  "browserExecutable": "dev",
  "url": "https://github.com/hamid-morsali-786/MdPersia/releases/dev"
}}"#,
            env!("CARGO_PKG_VERSION")
        );
        let _ = std::fs::write(staging.join("conversion-catalog.json"), catalog);
        let _ = std::fs::write(staging.join("THIRD_PARTY_NOTICES.txt"), "Development build notices\n");
        let _ = std::fs::write(staging.join("release-manifest.json"), "{}\n");
    }
    tauri_build::build();
}
