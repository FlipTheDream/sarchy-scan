#!/usr/bin/env python3
"""ClamAV release asset scan sub-agent.

Downloads the assets of a GitHub release, scans them with clamscan, and
uploads a Markdown security report back to the same release.

Exit codes:
    0  clean
    1  infected / needs review
    2  sub-agent or scan failure
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

EXIT_CLEAN = 0
EXIT_INFECTED = 1
EXIT_ERROR = 2

REPORT_NAME = "security_scan_report.md"


def verdict_for(returncode: int) -> tuple[str, int]:
    """Map a clamscan return code to a human verdict and a sub-agent exit code."""
    if returncode == 0:
        return "✅ CLEAN", EXIT_CLEAN
    if returncode == 1:
        return "⚠️ INFECTED / VERIFY", EXIT_INFECTED
    return "❌ SCAN ERROR", EXIT_ERROR


def build_report(repo_full_name: str, tag_name: str, verdict: str,
                 scan_logs: str, assets_dir: str) -> str:
    """Render the Markdown security audit report."""
    cleaned_logs = scan_logs.replace(assets_dir + os.sep, "assets:/")
    return (
        "# 🛡️ Autonomous AI Security Scan Report\n\n"
        f"- **Repository:** {repo_full_name}\n"
        f"- **Target Release:** `{tag_name}`\n"
        f"- **Scan Verdict:** **{verdict}**\n\n"
        "### ClamAV Engine Summary Logs:\n"
        "```text\n"
        f"{cleaned_logs}\n"
        "```\n\n"
        "---\n"
        "*Report generated autonomously by Sarchy-Scan execution.*\n"
    )


def run_security_scan(repo_full_name: str, tag_name: str) -> int:
    """Downloads, scans, and uploads a Markdown report for a specific release tag."""
    if not os.getenv("GITHUB_TOKEN"):
        print("[❌] Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        return EXIT_ERROR

    # Scan assets live in their own directory so the report and logs are never scanned.
    workdir = tempfile.mkdtemp(prefix="scan_agent_")
    assets_dir = os.path.join(workdir, "assets")
    os.makedirs(assets_dir)

    try:
        print(f"[*] Sub-Agent started for {repo_full_name} (Release: {tag_name})")

        print("[*] Downloading release assets...")
        subprocess.run(
            ["gh", "release", "download", tag_name,
             "-R", repo_full_name,
             "-D", assets_dir,
             "--clobber"],
            check=True,
        )

        # Drop reports left on the release by earlier runs so they aren't scanned or nested.
        prior_report = os.path.join(assets_dir, REPORT_NAME)
        if os.path.exists(prior_report):
            os.remove(prior_report)

        if not os.listdir(assets_dir):
            print(f"[❌] No assets found on release {tag_name}; nothing to scan.", file=sys.stderr)
            return EXIT_ERROR

        print("[*] Running ClamAV scan...")
        scan = subprocess.run(
            ["clamscan", "-r", "--stdout", assets_dir],
            capture_output=True,
            text=True,
        )
        scan_logs = scan.stdout + scan.stderr
        verdict, exit_code = verdict_for(scan.returncode)

        report_path = os.path.join(workdir, REPORT_NAME)
        with open(report_path, "w", encoding="utf-8") as rf:
            rf.write(build_report(repo_full_name, tag_name, verdict, scan_logs, assets_dir))

        print("[*] Uploading security report back to GitHub...")
        subprocess.run(
            ["gh", "release", "upload", tag_name, report_path,
             "-R", repo_full_name,
             "--clobber"],
            check=True,
        )
        print(f"[+] Verdict for {tag_name}: {verdict}")
        print(f"[+] Posted scan report back to {repo_full_name} for tag {tag_name}")
        return exit_code

    except subprocess.CalledProcessError as e:
        print(f"[❌] Subprocess Command Failed: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:
        print(f"[💥] Critical Sub-Agent Failure: {e}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Sub-Agent ClamAV Scanner")
    parser.add_argument("--repo", required=True, help="Full repository path (e.g., owner/repo)")
    parser.add_argument("--tag", required=True, help="The release tag name to scan")
    args = parser.parse_args()
    sys.exit(run_security_scan(args.repo, args.tag))


if __name__ == "__main__":
    main()
