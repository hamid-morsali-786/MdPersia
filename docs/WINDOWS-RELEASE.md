# Windows desktop distribution

The installer runs the existing React workspace in Tauri 2 and shared WebView2.
It includes a private frozen reader using the same Markdown/BiDi renderer,
preview worker and document-save implementation as the source app. It starts no
Vite server, system Python or system Node. PyInstaller directory mode avoids
extracting an executable on every launch.

## Small Setup and optional conversion

Setup must be at most **30,000,000 bytes**. `scripts/check-installer-size.py`
checks the actual NSIS executable, writes its size and SHA-256 receipt, and fails
the release if the limit is exceeded. This limit applies to the download, not
the installed footprint or the separate conversion pack.

The main package contains `reader/`, `assets/`, the conversion catalog and
notices. Reading, local images, fonts, Mermaid preview, editing, saving and RTL
Markdown output work without the conversion pack. PDF and Word require the
optional pack, which contains the full frozen engine, Playwright's private Node
driver and Chromium headless shell. Users install no developer runtimes.

The app checks only local conversion status on startup. Settings and a PDF/Word
request show the pack's size and an explicit download button. Downloading does
not start automatically. Users can cancel, retry, import the matching ZIP, or
remove installed conversion resources. Reading remains available during a
download and after removing the pack. Conversion works offline once installed.

The native executable pins the exact version, byte count and SHA-256 of its
pack. It verifies the downloaded or imported archive before extracting it,
rejects unsafe archive paths and symlinks, limits extraction sizes, runs an
engine check, then installs through a directory rename. Resources live under
the app's local data directory in `conversion-runtime/<sha256>`. Cancellation
and failure remove only owned temporary directories. Windows Job Objects stop
conversion process trees on cancel or exit.

Setup embeds Microsoft's small Evergreen WebView2 bootstrapper. If WebView2 is
missing or below the minimum version, installing that shared runtime requires
internet. A fresh Windows machine without WebView2 is therefore **not** a fully
offline installation scenario. Existing supported WebView2 is reused.

## Build and resource publication

Build on Windows x64 with Python 3.11 x64, Node 22, Rust/MSVC and the Windows SDK.
These are maintainer requirements, not user prerequisites.

```powershell
py -3.11 -m venv output/release-venv
output/release-venv/Scripts/python.exe -m pip install -r requirements-release.lock
output/release-venv/Scripts/python.exe scripts/build-small-windows.py
cd desktop-tauri
npm ci
npm test
npm run tauri build -- --bundles nsis -- --locked
cd ..
py -3.11 scripts/check-installer-size.py
```

The build produces `output/release/staging` for the reader and
`output/release/conversion-content` plus `conversion-packs/` for the converter.
`build-small-windows.py` creates a hash-named ZIP and catalog before compiling
Rust. The catalog is compiled into the native executable; do not substitute a
different catalog after compiling. Keep Playwright and its browser revision in
sync. The reader explicitly excludes converter dependencies and browsers.

The `Windows installer` workflow builds on Windows 2022 with committed
`Cargo.lock` and `--locked`, verifies both frozen engines, runs frontend and
native package tests, enforces the size limit, and checks installation and
registry commands. It saves Setup, the native directory, lockfile, catalog and
receipts as artifacts. After these checks, it publishes the optional ZIP to the
public `resources-v<version>` prerelease. Filenames contain their content hash;
existing pack assets are never overwritten. The repository used in the catalog
must have releases enabled and anonymous download access. Source builds default
to `Pezhm4n/MdPersia`; CI uses `GITHUB_REPOSITORY`.

## Installation and file associations

Installation is per user and does not require administrator privileges. Setup
registers `MdPersia.Markdown`, the native application icon, Start Menu and Open
With entries for `.md` and `.markdown` under HKCU. Existing Windows UserChoice
settings are respected. If another reader is the default, choose **Open with >
Choose another app > MdPersia > Always use this app** once.

Uninstall removes the handler only when its command still points at this
installation. Documents are never removed. Conversion resources can be removed
explicitly in Settings before uninstalling; uninstall does not erase app-local
user data. There is no automatic updater in this beta: install the next Setup
to upgrade. Preserve the app identifier between releases.

## Acceptance before sharing

```powershell
py -3.11 scripts/verify-reader-engine.py output/release/staging --output output/reader-qa
py -3.11 scripts/verify-frozen-engine.py output/release/conversion-content --output output/converter-qa
py -3.11 scripts/verify-windows-installer.py <Setup.exe> --output output/installed-win10-qa
```

Use a fresh output directory. The installer test backs up only the owned
Markdown registry entries, installs and reinstalls into an isolated directory,
checks manifest hashes and quoted handler commands, and launches the actual
installed Tauri app. It uninstalls and restores those registry entries in a
`finally` block. It does not change Windows UserChoice.

Native acceptance uses a separate WebView2 profile and CDP endpoint. Child PATH
contains only System32. Checks cover Persian paths, local images/fonts/Mermaid,
successive native and Windows shell opens into one queue, actual editor saves
with BOM/CRLF, close guards, download cancellation, same-length corrupt ZIP
rejection, real public download, Word/PDF output, watch rebuild/stop, process
cleanup, preferences and queue behavior after relaunch, and optional removal.
Screenshots and JSON receipts are retained. A reused runtime is an explicitly
marked resume scenario, not evidence of a fresh download.

Record the OS build, Setup hash, source revision and result for the exact file
shared. Windows 2022 CI and tests on a Windows 10 workstation do not establish
acceptance on a clean Windows VM or every hardware configuration.

## Signing and release trust

This beta Setup is unsigned unless a real publisher certificate is configured.
Windows SmartScreen can warn. Before a stable public release, sign both app and
installer with Authenticode and timestamp, then repeat acceptance on those
exact files. An updater signing key is a different mechanism and does not
establish Windows publisher trust. Keep private keys outside the repository.

Distribute Setup with its SHA-256 checksum. Preserve resource manifests,
catalog and CI revision to diagnose incomplete or mismatched installations.
