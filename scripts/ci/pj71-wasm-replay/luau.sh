#!/usr/bin/env bash
set -euo pipefail
repo_root="$PWD"
evidence="$repo_root/replay-evidence"
here=$(cd "$(dirname "$0")" && pwd)
title='Transform Editor creates a large exact Luau series while the browser main thread stays responsive'
source=857bd12b935579458914de18b59d8950b8bf71bd
producer=4c1ddc674097a5ab7391368050303208f99a6c72
receipt_producer="$producer"
if [[ "${PROFILE_D_ONLY:-false}" == true ]]; then
  source=2e9235ef1575551f4fa14c84ce150301e4022bcd
  receipt_producer="$source"
  test -s "$evidence/D-artifact-verify.log"
fi
test "$(git rev-parse HEAD)" = "$source"
test "$(git -C .ci-controller rev-parse HEAD)" = "$producer"
git diff HEAD --exit-code
test -s "$evidence/verify.log"
test "${MOZ_PROFILER_STARTUP:-}" = ""
node scripts/serve_wasm.mjs --root build-wasm-probe/deploy --port 6931 > "$evidence/server.log" 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for _ in $(seq 1 50); do
  curl -fsS -o /dev/null "$PJ_WASM_URL" && break
  sleep 0.2
done
curl -fsS -o /dev/null "$PJ_WASM_URL"
printf 'source=%s\nproducer_controller=%s\nreplay_controller=%s\n' "$source" "$receipt_producer" "$GITHUB_SHA" \
  > "$evidence/luau-replay-identity.txt"

# Gate: the exact source test, one Firefox worker and no profiler or overlays.
gate_status=0
(
  cd tests/wasm
  PLAYWRIGHT_JSON_OUTPUT_NAME="$evidence/luau-original.json" xvfb-run -a npx playwright test \
    --project=firefox --workers=1 --retries=0 --reporter=line,json --output "$evidence/luau-original-results" \
    editors.spec.js --grep "$title"
) 2>&1 | tee "$evidence/luau-original.log" || gate_status=$?
if [[ "$gate_status" == 0 ]]; then
  jq -e --arg title "$title" '.stats.expected == 1 and .stats.skipped == 0 and .stats.unexpected == 0 and .stats.flaky == 0 and ([.. | objects | select(has("file") and has("tests") and .file == "editors.spec.js") | .title] == [$title])' \
    "$evidence/luau-original.json"
  exit 0
fi
if [[ "${PROFILE_D_ONLY:-false}" == true && -s "$evidence/luau-original.json" ]]; then
  if ! jq -e --arg title "$title" '
    .stats.expected == 0 and .stats.unexpected == 1 and
    .stats.skipped == 0 and .stats.flaky == 0 and
    ([.. | objects | select(.title? == $title and .file? == "editors.spec.js")
       | .tests[] | select(.projectName == "firefox") | .results[]] as $r
     | ($r | length) == 1 and $r[0].status == "failed" and
       any($r[0].errors[]; .message | gsub("\u001b\\[[0-9;]*m"; "")
         | capture("Expected:[[:space:]]*< 100[[:space:]]+Received:[[:space:]]*(?<gap>[0-9]+([.][0-9]+)?)").gap | tonumber >= 100))
  ' "$evidence/luau-original.json"; then
    echo 'Diagnostic skipped: fresh unprofiled D failure is not the exact heartbeat gate.' | tee "$evidence/luau-profile-skip.log"
    exit "$gate_status"
  fi
fi
if [[ "$PROFILE_FAILED_LUAU" == true && -s "$evidence/luau-original.json" ]]; then
  # Reuse the pinned profile helper and expand ONLY its derivative test instrumentation.
  # The helper hashes the unmodified gate source/report and saves them with the profile.
  python3 "$here/luau-profile.py" .ci-controller/tests/wasm/profile_firefox_editor.cjs "$RUNNER_TEMP/luau-profile.cjs"
  # An explicit third argument switches the pinned helper to its historical Markdown reader.
  # Use its native JSON path and never alter either copy of the unprofiled gate report.
  report="tests/wasm/firefox-editors-report.json"
  test ! -e "$report"
  cp "$evidence/luau-original.json" "$report"
  cmp "$evidence/luau-original.json" "$report"
  profile_status=0
  PJ_SOURCE_SHA="$source" PJ_CONTROLLER_SHA="$receipt_producer" PJ_VALIDATION_ROLE=localized \
    PJ_ORIGINAL_RUN_ID="$GITHUB_RUN_ID" PJ_ORIGINAL_JOB_ID="$GITHUB_JOB" PJ_DIAGNOSTIC_CONTROLLER_SHA="$GITHUB_SHA" \
    xvfb-run -a node "$RUNNER_TEMP/luau-profile.cjs" "$repo_root" "$repo_root/.ci-controller" \
    2>&1 | tee "$evidence/luau-profile.log" || profile_status=$?
  printf '%s\n' "$profile_status" > "$evidence/luau-profile-exit.txt"
  if [[ -d firefox-editor-profile-results ]]; then
    mv firefox-editor-profile-results "$evidence/"
  fi
fi
exit "$gate_status"
