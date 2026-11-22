#!/usr/bin/env bash
set -euo pipefail
root="$PWD"
here=$(cd "$(dirname "$0")" && pwd)
evidence="$root/replay-evidence"
saved="$RUNNER_TEMP/pj71-baseline-D"
d=2e9235ef1575551f4fa14c84ce150301e4022bcd
e=84eabea0353dba95b7288166a618f5d827af1fc1
tree=22ea9ccccd54ab2e78bdc2f44ed0ef94c2ad2de5
patch_sha=a737da3dd27f114e9448dd7b36f49509c466cccad7edbd90bf44602bc5440c7a
expected_paths=$'pj_dialog_host/include/pj_plugins/host_qt/widget_binding.hpp\npj_dialog_host/src/panel_engine.cpp\npj_dialog_host/src/widget_binding.cpp'
title='Transform Editor creates a large exact Luau series while the browser main thread stays responsive'

case "$1" in
materialize)
  test -s "$evidence/D-artifact-verify.log"
  test "$(git rev-parse HEAD)" = "$d"
  git diff HEAD --exit-code
  mkdir "$saved"
  mv build-wasm-probe "$saved/acceptance"
  patch="$evidence/E-product.patch"
  base64 --decode "$here/panel-e.patch.b64" > "$patch"
  printf '%s  %s\n' "$patch_sha" "$patch" | sha256sum --check
  git apply --check --index --whitespace=error "$patch"
  git apply --index --whitespace=error "$patch"
  git diff --cached --check "$d"
  test "$(git diff --cached --name-only "$d")" = "$expected_paths"
  test "$(git write-tree)" = "$tree"
  cmd=(env GIT_AUTHOR_NAME='PlotJuggler candidate CI' GIT_AUTHOR_EMAIL=candidate-ci@example.invalid
       GIT_AUTHOR_DATE='2026-11-22T02:00:00Z' GIT_COMMITTER_NAME='PlotJuggler candidate CI'
       GIT_COMMITTER_EMAIL=candidate-ci@example.invalid GIT_COMMITTER_DATE='2026-11-22T02:00:00Z')
  commit=$("${cmd[@]}" git -c commit.gpgSign=false commit-tree "$tree" -p "$d" \
    -m 'Apply parsed panel updates without re-encoding changed widget data')
  test "$commit" = "$e"
  git checkout --detach "$e"
  test "$(git rev-parse HEAD HEAD^{tree} HEAD^)" = "$(printf '%s\n' "$e" "$tree" "$d")"
  git diff HEAD --exit-code
  git cat-file commit "$e" > "$evidence/E-product.commit"
  printf 'baseline=%s\ncandidate=%s\ntree=%s\npatch_sha256=%s\nworkflow=%s\nrun=%s\n' \
    "$d" "$e" "$tree" "$patch_sha" "$GITHUB_SHA" "$GITHUB_RUN_ID" > "$evidence/E-identity.txt"
  ;;
pair)
  test "$(git rev-parse HEAD HEAD^{tree} HEAD^)" = "$(printf '%s\n' "$e" "$tree" "$d")"
  git diff HEAD --exit-code
  node scripts/package_wasm.mjs --compression-profile localized \
    --source build-wasm-probe/pj_app --output build-wasm-probe/deploy
  receipt() {
    python3 .ci-controller/packaging/localization/wasm_receipt.py "$1" \
      --role localized --source-repository "$GITHUB_REPOSITORY" --source-sha "$e" \
      --controller-sha "$e" --controller-root . --kind acceptance \
      --cache build-wasm-probe/CMakeCache.txt --package build-wasm-probe/deploy \
      --extra 'build-wasm-probe/pj_app/plotjuggler4*.symbols' --output "$evidence/E-acceptance-receipt.json"
  }
  receipt capture
  receipt verify
  node scripts/wasm_localized_size_budget.mjs "$saved/acceptance/deploy/manifest.json" | tee "$evidence/D-size.log"
  node scripts/wasm_localized_size_budget.mjs build-wasm-probe/deploy/manifest.json | tee "$evidence/E-size.log"
  test -z "${MOZ_PROFILER_STARTUP:-}"
  run_trial() (
    trial=$1; package=$2
    node scripts/serve_wasm.mjs --root "$package" --port 6931 > "$evidence/$trial-server.log" 2>&1 &
    server=$!
    trap 'kill "$server" 2>/dev/null || true; wait "$server" 2>/dev/null || true' EXIT
    for _ in $(seq 1 50); do
      curl -fsS -o /dev/null "$PJ_WASM_URL" && break
      sleep .2
    done
    curl -fsS -o /dev/null "$PJ_WASM_URL"
    cd tests/wasm
    PLAYWRIGHT_JSON_OUTPUT_NAME="$evidence/$trial.json" xvfb-run -a npx playwright test \
      --project=firefox --workers=1 --retries=0 --reporter=line,json --output "$evidence/$trial-results" \
      editors.spec.js --grep "$title"
  )
  ds=0 es=0
  run_trial D "$saved/acceptance/deploy" 2>&1 | tee "$evidence/D.log" || ds=$?
  run_trial E "$root/build-wasm-probe/deploy" 2>&1 | tee "$evidence/E.log" || es=$?
  printf 'D=%s\nE=%s\n' "$ds" "$es" > "$evidence/pair-exits.txt"
  python3 "$here/evaluate_de.py" "$evidence/D.json" "$evidence/E.json" "$ds" "$es"
  ;;
*) exit 2;;
esac
