# Container image scan, 2026-10-28

Local scan with Trivy 0.76.1 (vulnerability scanner only, no secrets or misconfiguration checks) of the two images built from the `Dockerfile` on 2026-10-27:

| Image | Rows | Critical | High | Medium | Low | Unknown |
|---|---|---|---|---|---|---|
| `governed-claims-engine:local` (lexical-only runtime target) | 344 | 7 | 88 | 136 | 111 | 2 |
| `governed-claims-engine:semantic` (adds CPU torch 2.14.1, transformers 5.21.0, tokenizers, safetensors) | 344 | 7 | 88 | 136 | 111 | 2 |

The two finding sets are identical row for row. This is genuine, not a mix-up: the semantic image really contains the extra ML packages, and the scanner's database reports no known vulnerabilities for those versions.

## What the rows are
* **OS layer (Debian 12.15): 283 rows**, mostly low and medium (for example `libc6`, `libc-bin`, `bsdutils`). Two are critical and have no fixed version available: `libsqlite3-0` (CVE-2025-7458) and `zlib1g` (CVE-2023-45853).
* **Python packages: 61 rows**, of which 41 are Pillow records (see `PILLOW_ADVISORY_REVIEW.md`). The five critical Pillow rows are CVE-2026-112393, -112398, -112403, -112900 and -96639; all are fixed only in Pillow 13.0.0.
* 74 of the 344 rows list a fixed version.

## What this does and does not show
* It is triage evidence, not a safety statement. A scanner reports known records against package versions; it does not show that a vulnerable code path is reachable. For Pillow the reachability argument is in `PILLOW_ADVISORY_REVIEW.md` section 3.
* The scan was run locally by hand. **CI does not run it**, and CI builds and smoke-tests only the lexical-only image.
* The base image is pinned by digest, so OS findings change only when the digest is bumped or the scanner database updates.
