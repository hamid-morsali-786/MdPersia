# Local math preview hotfix — 2026-11-04

The local installer combines the accepted beta.3 native Setup with the reader
built from `d4c16367845556b9bdd70646a108f032008c8138`. The Tauri executable and
the pinned optional converter are reused; no Rust rebuild or remote build was
used. The installed resource manifest identifies the patch as `mathml-1` and
records both reader and native revisions. This is a preview/HTML correction;
the previously published optional converter and Word renderer are unchanged.

## Exact artifact

`output/releases/0.3.0-beta.3-math-fix/MdPersia_0.3.0-beta.3_math-fix_x64-setup.exe`

- Size: **25,901,735 bytes**, below the 30,000,000-byte Setup limit.
- SHA-256: `d942fe5ce6453c598492fc0be9b881ae6fc6bd85237116498ca8b2e547474707`.
- The embedded original Setup is separately checked against its accepted hash.
- The native UI and reader require no system Python or Node at runtime.
- This local hotfix is unsigned, like the original beta.

## Root cause and behavior

The original Markdown renderer had no math parser. Markdown interpreted TeX
backslashes and underscores as ordinary Markdown. The fix parses `$...$` and
`$$...$$` before those rules, converts to MathML, isolates direction as LTR and
uses native math typography. No math JavaScript, network fetch or startup task
is added. XML output is sanitized; invalid expressions retain a visible escaped
source fallback without hiding the following document.

Normalization is confined to parsed equations: lone line-ending backslashes,
escaped underscore before a brace, and typographic primes are accepted. Single
roman-unit letters and binary multiplication operators have regression checks.
Currency, fenced code and inline code remain literal. Commas are retained;
use `\,` for TeX spacing between a value and a unit.

## Windows 10 execution evidence

The exact Setup completed installation with exit code 0 into
`LocalAppData\Programs\MdPersia`. All **125 installed manifest entries** matched
their SHA-256 hashes. The file associations continue to select the same native
application. The installed application was then launched with an isolated
WebView2 profile and a PATH restricted to System32.

`scripts/verify-math-preview.py` exercised the actual native application, not a
development server. Both themes were rendered and screenshots inspected:

- User-provided fixture: **10 equations, 8 fractions, 3 boxed results**.
- Actual `HW.Ch1-part1-answers.fa.md`: **96 equations, 106 fractions,
  36 boxed results**.
- Offline context, LTR math, real fraction layout and zero math-error fallbacks.
- Zero page errors; original document SHA-256 unchanged after both runs.

Receipts/screenshots are under `output/math-fix/installed-qa/` and
`output/math-fix/actual-document-qa/`. Python regression results are retained
under `output/math-fix/`; Ruff passed for source, tests and both new scripts.
The final complete Python suite passed **179 tests** in 43.77 seconds;
`output/math-fix/pytest-exact-final.xml` records zero failures or skips.
The alias-version test previously hardcoded beta.2; it now verifies that the
alias exports the actual core version.

The external UX kit self-test returned **0/52**, with Node/Windows harness
failures. It was run separately and is not an application accessibility score.
The actual native screenshots and interaction checks above are separate
evidence. A full accessibility audit, clean-VM bootstrap, all display scales,
all TeX packages and new native PDF/Word math output were not verified.

No push, GitHub build, release creation or asset upload was performed.
