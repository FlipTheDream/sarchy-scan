# AGENTS.md

Instructions for AI agents working in this repository. Full documentation is in [README.md](README.md). The "Guide for AI agents" section there is the authoritative workflow.

## What this repo is

sarchy-scan is a one-shot ClamAV scanner. It downloads the assets of a GitHub **draft** release, scans them, and uploads `security_scan_report.md` back to that draft.

## Run a scan

```bash
GITHUB_TOKEN="<token>" ./run_agent.sh "<owner>/<repo>" "<tag>"
```

Exit codes: `0` clean, `1` infected or needs verification, `2` failure.

## Rules

- **Only scan draft releases.** Never point this at a published release.
- **Never publish a release.** Publishing is a human decision.
- **Do not publish on exit `1` or `2`.** Treat a missing report as a failure, not as clean.
- **Pass the token through the environment only.** Never write it to a file, log it, or put it on the command line.
- **Don't edit `scan_agent.py`, `run_agent.sh`, or `Dockerfile` during a release run.** Changes need their own review.
- **Run the tests after any code change:** `python3 -m unittest discover -s tests -v`

## Editing this repo

- Keep the code and docs consistent. If you change behavior, update README.md.
- Match the existing style: plain Python 3 standard library, no new dependencies.
