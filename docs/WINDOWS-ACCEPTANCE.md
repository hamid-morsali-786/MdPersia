# Windows beta 0.3.0-beta.2 acceptance

The delivered small Setup was built from
`b919fa9f0c9e6b098c6144e4f7241423600213dc` in
[Windows installer run 40664741031](https://github.com/Pezhm4n/MdPersia/actions/runs/40664741031).
Subsequent documentation and acceptance-script changes do not change this
binary. This is the existing MdPersia workspace, with a small reader payload
and an explicitly downloaded conversion pack.

## Artifact identity and measured size

| Item | Bytes |
|---|---:|
| `MdPersia_0.3.0-beta.2_x64-setup.exe` | 15,832,533 |
| Setup limit | 30,000,000 |
| Main installed files | 35,154,353 |
| Optional conversion ZIP download | 182,734,982 |
| Optional installed conversion files | 442,216,221 |

Installed-file measurements exclude the shared WebView2 runtime, user profiles
and caches. They are file lengths, not allocated disk space or RAM measurements.

Setup SHA-256:

```text
d07b235ad93c3a97990a34c52bddc6453690c82592626c2118f9ad50278891f9
```

The matching conversion ZIP has SHA-256
`04eeca0110bf86dab79c88b4fd6a42c455e616d2cd191008c716966cc8b9f340`.
Its immutable public download is pinned in the installed application. Native
acceptance downloaded it without GitHub credentials and verified installation.

## Actual installed-app acceptance

Test host: Windows 10 x64, build 19045. WebView2 reported `156.0.4314.50`.
The test installed and reinstalled the exact Setup into an isolated folder
whose path contains a space. It checked every resource-manifest hash, native
file-handler quoting and executable icon registration. Child PATH contained
only `C:\Windows\System32`; Python and Node were not available through PATH.
The application used a separate WebView2 profile, not the user's normal one.

The final run passed these checks:

- Open a Persian Markdown filename before installing the conversion engine.
- Render local images, local Vazirmatn and Mermaid in the real native preview.
- Open three files successively, preserve the queue and deduplicate reopens.
- Open a file through the registered Windows shell handler into the same window.
- Edit the live preview and save actual file bytes, preserving UTF-8 BOM and CRLF.
- Cancel the close guard without losing unsaved edits, then save them.
- Scan an actual directory through native IPC.
- Require explicit consent to download when PDF or Word is requested.
- Keep keyboard focus inside the optional-engine dialog, close with Escape and
  return focus to the initiating control; no horizontal dialog overflow.
- Reject an exact-length corrupt ZIP through the native import command before
  extracting anything, and remove temporary files.
- Cancel a download without leaving an installed or partial conversion pack.
- Retry through the UI, download the actual public pack and continue reading
  while the download runs.
- Generate three actual Word files, rebuild one after an external file change
  in Watch mode, and stop watching.
- Exit without leaving reader, engine or headless-browser processes behind.
- Relaunch with saved settings and only the newly requested file in the queue.
- Reuse the installed conversion resources and generate an actual PDF.
- Remove the optional engine through the UI, continue reading, and preserve
  the generated documents.
- Uninstall the app while retaining test documents, and restore the pre-test
  owned Markdown registry entries.

No page errors were recorded in the final run. Fresh-profile launch to rendered
heading measured **2.190 seconds**, and the subsequent launch measured
**1.637 seconds**. These measurements include the CDP attachment and apply to
this workstation and test document; they are not hardware-independent targets.
The reader-only frozen-engine preview test measured 0.181 seconds separately.

JSON receipts and screenshots are retained locally under
`output/installer-qa/small-locked-win10/`. The release output includes copies of
the installer, native-app and reader receipts, plus the catalog and size report.

## Other checks

- Python: 174 passed, zero failures or skips; JUnit receipt in
  `output/pytest-small-final.xml`.
- TypeScript: 33 passed; production TypeScript/Vite build completed. Vite still
  reports the existing editor-chunk size and runtime font-path warnings; the
  installed native preview's local font check passed.
- Ruff: `ruff check src tests` passed.
- Native Rust: two package tests passed in CI, covering archive path rejection
  and catalog/version/hash metadata.
- Full frozen converter: actual PDF and Word generation with Mermaid passed in
  CI, including Windows verbatim resource-path normalization.
- Setup size gate, installed-resource hashes, reinstall and uninstall passed
  in CI as well as the Windows 10 installed-app checks above.

The external UX kit self-test reported **12/52 checks passed** on this host.
That command tests the kit's own examples, not MdPersia. It failed on missing
kit Playwright dependencies, Windows shell assumptions and encoding issues.
It is not an application accessibility score or an application pass. Native
screenshots in both themes and the keyboard checks above are separate evidence.

## Limits and unresolved observations

`Get-AuthenticodeSignature` reports `NotSigned`. This is an unsigned beta;
publisher trust and SmartScreen reputation are not established.

WebView2 was already installed on the Windows 10 workstation. A clean VM,
missing-WebView2 bootstrap installation, 32-bit Windows and a full accessibility
audit are unconfirmed. The corrupt-ZIP import path was exercised through native
IPC; selecting a valid pack with the native ZIP picker was not separately
automated.

An earlier candidate run completed download, conversion and removal, but timed
out waiting for the management dialog after removal. Its cause was not
established. The final exact-build run passed removal and continued reading;
the earlier observation must not be presented as a diagnosed and fixed defect.
