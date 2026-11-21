#!/usr/bin/env bash
set -euo pipefail
repo=reliable-ly0411/PlotJuggler-zh-CN
source_sha=857bd12b935579458914de18b59d8950b8bf71bd
controller_sha=4c1ddc674097a5ab7391368050303208f99a6c72
run=44911705085
archive_id=14710382624
digest=e6f4b11aaaa8d0f5685d0a89cbdca8555028648822113d8c350a613c55e4084f
epoch=b8c79238cd4cf7063f27bdb045d8e133d203292e926c871a380bd1398dacbce2
observations=35e2c2e7fe53f3e12ef4ec25c6caf2bc3b8853373a0b590c02b3d98a97185aef
evidence="$PWD/replay-evidence"
mkdir -p "$evidence"
here=$(cd "$(dirname "$0")" && pwd)
test "$(git rev-parse HEAD)" = "$source_sha"
test "$(git -C .ci-controller rev-parse HEAD)" = "$controller_sha"
test "$(git -C .replay-controller rev-parse HEAD)" = "$GITHUB_SHA"

case "$1" in
verify)
  test "$GITHUB_REPOSITORY" = "$repo"
  path="repos/$repo/actions/artifacts/$archive_id"
  gh api "$path" > "$evidence/archive-metadata.json"
  jq -e --arg digest "sha256:$digest" --arg sha "$source_sha" --argjson run "$run" --argjson id "$archive_id" \
    '.id == $id and .workflow_run.id == $run and .digest == $digest and .expired == false
     and .name == ("wasm-localized-acceptance-" + $sha + "-1")' "$evidence/archive-metadata.json"
  archive="$RUNNER_TEMP/pj71-acceptance.zip"
  gh api "$path/zip" > "$archive"
  printf '%s  %s\n' "$digest" "$archive" | sha256sum --check
  unzip -q "$archive"
  rm "$archive"
  cp validation-receipts/acceptance.json "$evidence/original-acceptance-receipt.json"
  jq -e --arg run "$run" '.validation_run.id == $run and .validation_run.attempt == "1"' validation-receipts/acceptance.json
  python3 .ci-controller/packaging/localization/wasm_receipt.py verify \
    --role localized --source-repository "$repo" --source-sha "$source_sha" \
    --controller-sha "$controller_sha" --kind acceptance \
    --package build-wasm-probe/deploy --package build-wasm-probe/deploy-presets \
    --extra 'build-wasm-probe/pj_app/plotjuggler4*.symbols' \
    --extra 'build-wasm-probe/pj_app/scene3d_capability_probe.*' \
    --extra build-wasm-probe/pj_app/qtloader.js --extra build-wasm-probe/pj_app/qtlogo.svg \
    --extra .emsdk/upstream/emscripten/emrun.py --output validation-receipts/acceptance.json \
    | tee "$evidence/verify.log"
  ;;
test)
  git diff HEAD --exit-code
  for record in "epoch:$epoch" "serial-observations:$observations"; do
    kind=${record%%:*}
    overlay="$RUNNER_TEMP/$kind.patch"
    base64 --decode "$here/$kind.patch.b64" > "$overlay"
    printf '%s  %s\n' "${record#*:}" "$overlay" | sha256sum --check | tee -a "$evidence/overlays.log"
    git apply --check "$overlay"
    git apply "$overlay"
  done
  git diff HEAD --check
  test "$(git diff --name-only HEAD)" = $'tests/wasm/log_widget_targeted.spec.js\ntests/wasm/presets.spec.js'
  printf 'source=%s\nproducer_controller=%s\nreplay_controller=%s\nreplay_run=%s\narchive=%s\ndigest=%s\n' \
    "$source_sha" "$controller_sha" "$GITHUB_SHA" "$GITHUB_RUN_ID" "$archive_id" "$digest" > "$evidence/replay-identity.txt"
  node scripts/serve_wasm.mjs --root build-wasm-probe/deploy --port 6931 > "$evidence/server.log" 2>&1 &
  trap 'kill "$!" 2>/dev/null || true' EXIT
  for _ in $(seq 1 50); do
    curl -fsS -o /dev/null "$PJ_WASM_URL" && break
    sleep 0.2
  done
  curl -fsS -o /dev/null "$PJ_WASM_URL"
  cd tests/wasm
  browser=()
  case "$REPLAY_BROWSER" in
    chromium) ;;
    firefox) browser=(xvfb-run -a);;
    *) exit 2;;
  esac
  run_exact() {
    local label=$1 expected=$2
    shift 2
    local result=0
    PLAYWRIGHT_JSON_OUTPUT_NAME="$evidence/$label.json" "${browser[@]}" npx playwright test \
      --project="$REPLAY_BROWSER" --workers=1 --reporter=line,json --trace=retain-on-failure \
      --output "$evidence/$label-results" "$@" 2>&1 | tee "$evidence/$label.log" || result=$?
    test "$result" -eq 0 && jq -e --argjson count "$expected" \
      '.stats.expected == $count and .stats.skipped == 0 and .stats.unexpected == 0 and .stats.flaky == 0' \
      "$evidence/$label.json"
  }
  status=0
  run_exact log 2 log_widget_targeted.spec.js --grep 'a native Log restores (native|legacy official widget) layout and epoch history' || status=1
  if [[ "$REPLAY_BROWSER" == chromium ]]; then
    run_exact serial 1 presets.spec.js --grep 'a sample that fails releases what it staged and leaves the open sample as it was' || status=1
  fi
  exit "$status"
  ;;
*) exit 2;;
esac
