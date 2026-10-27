# Dependency and supply-chain report (Milestone 5)

Run 2026-10-27. Tool: `pip-audit 2.9.0`, installed in an **isolated throw-away venv outside the project and outside the shared
Anaconda environment** (it is a CI tool, not a project dependency). It queries public advisory data (PyPI/OSV), so it sends package
names and versions to those services. It only finds *publicly known* advisories; "clean" never means "secure".

## Results

| Scope | Before this milestone | After |
|---|---|---|
| **Container runtime closure** (`requirements-container.txt`, 76 hash-pinned wheels) | gradio 6.10.0 (3), pillow 12.3.0 (37), starlette 0.52.1 (5) | **pillow 12.3.0 (37) only** |
| **Project venv** (everything installed incl. optional torch stack and dev tools) | the above + pip 23.2.1 (7) + pytest 7.4.0 (1) | **pillow 12.3.0 (37) only** |

Actions taken (all in the project venv; the shared Anaconda environment was **not** modified):

| Package | Change | Why | Verification |
|---|---|---|---|
| gradio | 6.10.0 -> **6.30.0** (released 2026-10-08) | fixes the three Gradio advisories (cookie-injection session fixation, FileExplorer path traversal, audio cache key); pulls starlette 1.10.0 | full suite green; browser re-check of the UI; VARIANTS_REPORT.md byte-identical and every workflow outcome (status, citations, flags) identical to the M3 results (only timings differ) |
| starlette | 0.52.1 -> **1.10.0** (via gradio 6.30.0) | fixes five advisories (Host-header URL reconstruction, form-parsing limits, path validation) | same |
| huggingface_hub | 1.33.0 -> **2.3.0** | gradio 6.30.0 allows `<3` again; restores the exact version used for the M2/M3 results | `pip check` clean; 3 real-model tests pass; `VARIANTS_REPORT.md` unchanged |
| pip (venv) | 23.2.1 -> 26.2.x | seven advisories | `pip check` |
| pytest (venv) | 7.4.0 -> **9.0.3** | local `/tmp/pytest-of-user` denial-of-service advisory | full suite green |

## Accepted risk: Pillow 12.3.0 (full analysis: `PILLOW_ADVISORY_REVIEW.md`)

* **37 advisories reviewed individually** (4 CRITICAL, 22 HIGH, 11 MODERATE), all fixed only in Pillow 13.0.0, which Gradio 6.30.0 (the latest release, checked 2026-10-27) forbids
  (`pillow<13`). No compatible patched version exists. An isolated experiment showed the demo tests pass on Pillow 13.0.0, but that combination is unsupported and the tests exercise no image code.
* **Reachability:** no image-decoding path is reachable through the application as built and served (static source review + live probing + a component-type guard test). The review also
  found an unauthenticated upload route (`POST /gradio_api/upload` -> 200) that was **not** in the M4 review; it, the file-serving routes and the icon route are now blocked and tested.
* **Not accepted on the grounds of loopback binding.** The acceptance rests on the tested controls. Conditions under which the application must NOT be exposed are in section 7 of that document.
* **Enforcement:** `governance/accepted_advisories.json` lists the 37 ids, the exact Pillow version (12.3.0) and an expiry (2026-12-31). CI runs `scripts/check_audit_allowlist.py` on the
  `pip-audit` JSON and fails on any other advisory, any other package, a different Pillow version, or after expiry.
* **Exit criteria:** upgrade to Pillow >= 13.0.0 as soon as a Gradio release permits it, or replace the UI framework; then delete the acceptance entry.
## Not covered / honest gaps

* The shared Anaconda environment still contains older Gradio 6.10.0, Starlette 0.52.1, pip 23.3.1 and pytest 7.4.0 (with the advisories above).
  It was deliberately left untouched per the project rules; the test suite also passes there (see PROJECT_STATUS.md).
* The optional semantic stack (torch 2.14.1, transformers 5.21.0, sentence-transformers 6.2.0, tokenizers, safetensors) is version-pinned but **not hash-pinned**
  and is audited only via the project-venv scan above (no advisories reported for it on this date).
* The container closure was resolved on Windows; pip evaluates environment markers for the host, so a Linux-only dependency could be missing.
  The Dockerfile installs with `--require-hashes` *without* `--no-deps`, which makes the image build **fail loudly** in that case instead of failing at run time.
  This has **not been exercised** (no Docker daemon).
* No SBOM (CycloneDX/SPDX) generated, no licence review, no malware/typosquat check, no reproducible-build verification, no signature verification of wheels
  beyond hash pinning to PyPI's published digests (hash pinning protects against tampering after publication, not against a malicious release).
* Base image `python:3.11-slim-bookworm` pinned by digest `sha256:f06d01d4...` (resolved from the registry API 2026-10-27, linux/amd64 and linux/arm64);
  OS packages inside it were **not scanned** (no Docker/Trivy run).
* Static analysis: `ruff --select S` (flake8-bandit rules) on `src` and `scripts` passes after replacing four `assert` statements used for type narrowing with explicit errors
  and adding a URL-scheme guard to the one-off model-metadata request. It is a lint-level scan, not a security review.

## Reproduce

```
# in an ISOLATED venv (not the project venv, not the shared env):
pip install "pip-audit==2.9.0"
pip-audit --disable-pip --no-deps -r requirements-container.txt
pip-audit --path .venv/Lib/site-packages          # everything installed in the project venv (Windows layout)
# regenerate the hash-pinned container requirements (needs network):
python scripts/make_container_requirements.py
```
</content>
