# 🛡️ sarchy-scan

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/FlipTheDream/sarchy-scan)](https://github.com/FlipTheDream/sarchy-scan/commits/main)
[![ClamAV 1.5.4](https://img.shields.io/badge/ClamAV-1.5.4-2E7D32)](https://hub.docker.com/r/clamav/clamav/tags)
[![Docker](https://img.shields.io/badge/Docker-required-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GitHub CLI](https://img.shields.io/badge/GitHub%20CLI-gh-181717?logo=github&logoColor=white)](https://cli.github.com/)

**sarchy-scan** is a short-lived ClamAV sub-agent for GitHub releases. It downloads the assets of a **draft** release, scans them locally with `clamscan`, and attaches a Markdown security report to the same draft. A developer reviews the assets and report before publishing.

Scanning runs on your own machine or build runner instead of GitHub Actions, which keeps Actions minutes and fees down. There is no webhook server: the agent runs as a one-shot CLI container.

---

## Contents

- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Requirements](#requirements)
- [Exit codes](#exit-codes)
- [Project layout](#project-layout)
- [Running the tests](#running-the-tests)
- [Guide for AI agents](#guide-for-ai-agents)
- [License](#license)

---

## How it works

```
Orchestrator         run_agent.sh                      GitHub draft release
     │                    │                                   │
     │  build artifacts   │                                   │
     │  create draft ────────────────────────────────────────►│
     │                    │                                   │
     │  run_agent.sh ───► │ 1. build image                    │
     │                    │ 2. freshclam (refresh signatures) │
     │                    │ 3. gh release download ◄──────────│ assets
     │                    │ 4. clamscan -r assets/            │
     │                    │ 5. build Markdown report          │
     │                    │ 6. gh release upload ────────────►│ security_scan_report.md
     │  ◄── exit code ────│                                   │
     │                    │                                   │
     │         Developer reviews assets + report, then publishes (human gate)
```

Step 6 uses `--clobber`, so each run replaces the previous report on the draft.

## Quick start

```bash
export GITHUB_TOKEN="$(gh auth token)"   # or a fine-grained PAT (see Requirements)
./run_agent.sh owner/repo v1.2.3
echo $?                                  # 0 clean · 1 infected/verify · 2 failure
```

`run_agent.sh` takes exactly two arguments, the repository (`owner/repo`) and the release tag. It refuses to run if `GITHUB_TOKEN` is unset.

## Requirements

| Requirement | Notes |
| --- | --- |
| Docker | Daemon must be running and reachable by the current user. |
| GitHub token | Fine-grained PAT with **Contents: Read and write** on the target repo. Metadata: Read is granted automatically. |
| Network | Needed for `docker build`, `freshclam` signature updates, and the GitHub API. |

ClamAV is **not** installed on the host. It runs inside the container, which uses the official [`clamav/clamav`](https://hub.docker.com/r/clamav/clamav) image.

## Exit codes

| Code | Meaning | Recommended orchestrator action |
| --- | --- | --- |
| `0` | Clean. No threats found. | Proceed to the human review gate. |
| `1` | Infected or needs review. | **Do not publish.** Surface the report to the developer. |
| `2` | Failure: missing token, no assets, download/upload error, or scan error. | **Do not publish.** Investigate and rerun. |

A `0` only means the scanner found nothing. A developer must still check the draft and the report before publishing.

## Project layout

| File | Purpose |
| --- | --- |
| [`scan_agent.py`](scan_agent.py) | Sub-agent: download, scan, report, upload, cleanup. |
| [`Dockerfile`](Dockerfile) | Image built on the official ClamAV image, adds Python and `gh`. |
| [`run_agent.sh`](run_agent.sh) | Orchestration hook: volume, build, signature refresh, scan. |
| [`tests/test_scan_agent.py`](tests/test_scan_agent.py) | Unit tests for verdict mapping and report rendering. |
| [`.dockerignore`](.dockerignore) | Keeps tests, git metadata, and specs out of the image. |
| [`LICENSE`](LICENSE) | GNU GPL v3. |

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` | *(required)* | Token used by `gh` inside the container. |
| `IMAGE_NAME` | `release-scan-subagent` | Local image name. |
| `CACHE_VOLUME` | `clamav_db_cache` | Docker volume holding ClamAV signatures. |
| `CLAMAV_VERSION` | `1.5.4` | Build argument: ClamAV image tag used as the base. |

To change the ClamAV version: `docker build --build-arg CLAMAV_VERSION=<tag> .` or edit the default in the `Dockerfile`. Check [the available tags](https://hub.docker.com/r/clamav/clamav/tags) first.

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

The tests cover verdict mapping and report rendering. They don't need Docker or network access.

---

## Guide for AI agents

This section is written for automation agents that invoke sarchy-scan. Follow it exactly.

### Purpose and scope

- sarchy-scan **only scans draft releases**. Do not point it at a published release.
- It is a **gate**, not an approval. A `0` exit code means no signatures matched. It does not certify the software as safe.
- The human developer makes the publish decision.

### Preconditions

Before invoking, confirm:

1. The target release exists as a **draft** and all build artifacts are uploaded to it.
2. `GITHUB_TOKEN` is available from your secret store. Never hard-code it and never pass it as a command-line argument.
3. Docker is running on the host.

### Invocation

```bash
GITHUB_TOKEN="$TOKEN_FROM_SECRET_STORE" ./run_agent.sh "<owner>/<repo>" "<tag>"
```

- Arguments are positional: repository first, tag second.
- Run from the sarchy-scan repository root, or call the script by absolute path.
- Each run rebuilds the image, refreshes signatures, and overwrites the report asset on the draft.

### Interpreting the result

1. Read the exit code.
2. **`0`:** mark the release as *scan passed, awaiting human review*. Don't publish it yourself.
3. **`1`:** mark the release as *blocked: infection or verification needed*. Don't publish. Tell the developer that `security_scan_report.md` on the draft lists the flagged files.
4. **`2`:** mark the release as *scan failed*. Don't publish. Don't treat a failed run as clean. Check the log for the cause. Common causes are a missing token, a draft without assets, or a permission error.

### Rules

- **Never publish** a release on your own. Publishing is the human gate.
- **Never treat a missing report as clean.** If the upload fails, the exit code is `2`.
- **Don't scan more than needed.** The scanner reads every asset on the draft, so keep the draft limited to the release artifacts.
- **Don't edit `scan_agent.py`, `run_agent.sh`, or the `Dockerfile`** as part of a release run. Changes to these files need their own review and test pass.
- **Reports are overwritten** on each run. If a developer needs an earlier report, they must save it before rerunning.

### Reading the report

The report is `security_scan_report.md` on the draft. It includes the repository, the release tag, the verdict, the ClamAV engine version, and a per-file log with paths shown relative to `assets:/`.

Signature matches appear as `assets:/<file>: <SignatureName> FOUND`. Clean files appear as `OK`.

---

## License

sarchy-scan is free software under the [GNU General Public License v3.0](LICENSE).
