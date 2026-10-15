# SPDX-License-Identifier: MPL-2.0
"""Merge the official Qt5 branch, preserving custom commits and refusing conflicts."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def sync(args):
    repo = Path(args.repo).resolve()
    report = {"result": "failed", "changed": False, "branch": args.branch}
    merging = False

    def git(*arguments, check=True):
        result = subprocess.run(
            [os.environ.get("GIT", "git"), "-C", str(repo), *arguments],
            text=True, encoding="utf-8", errors="replace", capture_output=True,
        )
        if check and result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result

    def output():
        path = Path(args.report).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
                stream.write(f"changed={str(report['changed']).lower()}\n")
                stream.write(f"ref={report.get('after', report.get('before', ''))}\n")

    try:
        if git("status", "--porcelain").stdout.strip():
            raise RuntimeError("Refusing to synchronize a dirty worktree")
        branch = git("symbolic-ref", "--short", "HEAD").stdout.strip()
        if branch != args.branch:
            raise RuntimeError(f"Expected branch {args.branch!r}, found {branch!r}")
        report["before"] = git("rev-parse", "HEAD").stdout.strip()
        git("fetch", "--no-tags", args.upstream_url, args.upstream_ref)
        upstream = git("rev-parse", "FETCH_HEAD").stdout.strip()
        report["upstream"] = upstream
        cmake = git("show", f"{upstream}:CMakeLists.txt").stdout
        version = re.search(r"\bVERSION\s+(\d+)\.(\d+)\.(\d+)", cmake)
        if not version or int(version[1]) != 3:
            report["result"] = "unsupported_major"
            raise RuntimeError("Upstream is no longer Qt5 PlotJuggler 3.x; manual migration is required")
        report["upstream_version"] = ".".join(version.groups())
        if git("merge-base", "--is-ancestor", upstream, "HEAD", check=False).returncode == 0:
            report.update(result="up_to_date", after=report["before"])
            return 0
        merge = git("-c", "user.name=github-actions[bot]", "-c",
                    "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                    "merge", "--no-ff", "--no-commit", upstream, check=False)
        merging = True
        if merge.returncode:
            report["conflicts"] = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
            report["merge_output"] = merge.stdout + merge.stderr
            report["result"] = "conflict" if report["conflicts"] else "merge_failed"
            raise RuntimeError("Upstream merge conflicts; the customization branch was not updated")
        if args.validate:
            result = subprocess.run(
                [sys.executable, "tests/check_translations.py", "--fresh"], cwd=repo,
                text=True, encoding="utf-8", errors="replace", capture_output=True,
            )
            report["validation"] = result.stdout + result.stderr
            if result.returncode:
                report["result"] = "validation_failed"
                raise RuntimeError("Merged translations need review; the customization branch was not updated")
        git("-c", "user.name=github-actions[bot]", "-c",
            "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit", "-m", f"sync: merge upstream Qt5 branch at {upstream[:12]}")
        merging = False
        report["after"] = git("rev-parse", "HEAD").stdout.strip()
        # Ordinary push rejects a concurrent branch update. Never force or reset the remote.
        if args.push:
            git("push", "origin", f"HEAD:refs/heads/{args.branch}")
        report.update(result="merged_and_pushed" if args.push else "merged_locally", changed=True)
        return 0
    except (RuntimeError, OSError) as error:
        report["error"] = str(error)
        print(str(error), file=sys.stderr)
        return 1
    finally:
        if merging:
            git("merge", "--abort", check=False)
        output()
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch", default="zh-CN")
    parser.add_argument("--upstream-url", default="https://github.com/PlotJuggler/PlotJuggler.git")
    parser.add_argument("--upstream-ref", default="main")
    parser.add_argument("--report", required=True)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--push", action="store_true")
    sys.exit(sync(parser.parse_args()))
