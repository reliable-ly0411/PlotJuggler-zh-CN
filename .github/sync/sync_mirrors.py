#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Fast-forward only the two upstream mirror refs, without checking out upstream code."""

import argparse
import http.client
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

REPOSITORY = "reliable-ly0411/PlotJuggler-zh-CN"
UPSTREAM = "PlotJuggler/PlotJuggler"
BRANCHES = {"main-3.x": "main-3.x", "main": "main"}
SHA = re.compile(r"[0-9a-f]{40}\Z")


class SyncError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SyncError(f"Unexpected GitHub API redirect (HTTP {code}); no request retried")



def http_failure_kind(exc):
    """Classify selected API failures without putting GitHub response text in reports."""
    if exc.code not in (403, 422, 429):
        return None
    remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
    if exc.code == 429 or (exc.code == 403 and remaining == "0"):
        return "rate_limit"

    # The response is untrusted. Read a bounded JSON body and emit only fixed labels.
    try:
        body = exc.read(4097) if exc.fp is not None else b""
        payload = json.loads(body) if 0 < len(body) <= 4096 else None
    except (http.client.HTTPException, OSError, RecursionError, ValueError):
        payload = None
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str):
        return "forbidden_unspecified" if exc.code == 403 else None
    message = message.casefold()
    if exc.code == 403 and ("secondary rate limit" in message or "api rate limit exceeded" in message):
        return "rate_limit"
    if "workflow" in message and (
        "without `workflow` scope" in message or
        "without workflows permission" in message or
        '"workflows" permission' in message or
        "'workflows' permission" in message
    ):
        return "workflow_permission"
    if any(hint in message for hint in (
        "repository rule violations", "protected branch hook declined",
        "changes must be made through a pull request",
    )):
        return "branch_rule"
    if exc.code == 403 and message == "resource not accessible by integration":
        return "integration_access_denied"
    return "forbidden_unspecified" if exc.code == 403 else None


class GitHub:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, method, path, body=None):
        if not path.startswith((f"/repos/{REPOSITORY}/", f"/repos/{UPSTREAM}/")):
            raise SyncError("Unexpected repository API path")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "PlotJuggler-upstream-mirror-sync",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"https://api.github.com{path}", data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            kind = http_failure_kind(exc)
            detail = f" [{kind}]" if kind else ""
            raise SyncError(f"GitHub {method} {path}: HTTP {exc.code}{detail}; no request retried") from None
        except (OSError, ValueError) as exc:
            raise SyncError(f"GitHub {method} {path}: request failed; no request retried") from exc


def branch_sha(api, repository, branch):
    result = api.request("GET", f"/repos/{repository}/git/ref/heads/{branch}")
    if not isinstance(result, dict) or not isinstance(result.get("object"), dict):
        raise SyncError(f"Invalid ref response for {repository}:{branch}")
    obj = result["object"]
    sha = obj.get("sha", "")
    if result.get("ref") != f"refs/heads/{branch}" or obj.get("type") != "commit" or not SHA.fullmatch(sha):
        raise SyncError(f"Invalid commit ref for {repository}:{branch}")
    return sha


def sync_branch(api, branch, push):
    if branch not in BRANCHES:
        raise SyncError("Only main-3.x and main are upstream mirrors")
    upstream_branch = BRANCHES[branch]
    result = {"branch": branch, "upstream_branch": upstream_branch, "status": "checking"}
    try:
        before = branch_sha(api, REPOSITORY, branch)
        upstream = branch_sha(api, UPSTREAM, upstream_branch)
        result.update(before=before, upstream=upstream)
        if before == upstream:
            result["status"] = "already_current"
            return result
        comparison = api.request("GET", f"/repos/{REPOSITORY}/compare/{before}...{upstream}")
        if not isinstance(comparison, dict) or not isinstance(comparison.get("merge_base_commit"), dict):
            raise SyncError("Invalid upstream comparison response")
        if (
            comparison.get("status") != "ahead"
            or comparison.get("behind_by") != 0
            or comparison.get("ahead_by", 0) <= 0
            or comparison.get("merge_base_commit", {}).get("sha") != before
        ):
            raise SyncError("Not a fast-forward: preserve local history and require review")
        result["upstream_commits"] = comparison["ahead_by"]
        if not push:
            result["status"] = "would_fast_forward"
            return result
        if branch_sha(api, REPOSITORY, branch) != before:
            raise SyncError("Mirror changed during comparison; no update attempted")
        # GitHub rejects non-fast-forward writes atomically. Never force, merge,
        # create/delete refs, touch tags, or change branch protection/settings.
        # No automatic retry: a failed response can have an uncertain outcome.
        result["write_attempted"] = True
        api.request("PATCH", f"/repos/{REPOSITORY}/git/refs/heads/{branch}", {"sha": upstream, "force": False})
        result["after"] = branch_sha(api, REPOSITORY, branch)
        if result["after"] != upstream:
            raise SyncError("Mirror differs after update; inspect current ref before any retry")
        result["status"] = "fast_forwarded"
    except (SyncError, KeyError, TypeError) as exc:
        result.update(status="blocked", error=str(exc))
    return result


def run(api, push):
    results = [sync_branch(api, branch, push) for branch in BRANCHES]
    return {"repository": REPOSITORY, "upstream_repository": UPSTREAM, "push": push, "branches": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", action="store_true", help="Apply safe fast-forwards (default: read-only)")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    repository = os.environ.get("GITHUB_REPOSITORY", REPOSITORY)
    if repository != REPOSITORY:
        parser.error("This controller is restricted to its configured repository")
    token = os.environ.get("GH_TOKEN", "")
    if args.push and not token:
        parser.error("--push requires the workflow's short-lived GH_TOKEN")
    report = run(GitHub(token), args.push)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(any(item["status"] == "blocked" for item in report["branches"]))


if __name__ == "__main__":
    sys.exit(main())
