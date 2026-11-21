#!/usr/bin/env bash
set -euo pipefail
root="$PWD"
here=$(cd "$(dirname "$0")" && pwd)
evidence="$root/replay-evidence"
saved="$RUNNER_TEMP/pj71-original-A"
a=857bd12b935579458914de18b59d8950b8bf71bd
d=2e9235ef1575551f4fa14c84ce150301e4022bcd
tree=483bb27b54c929697295978fc66a1c59da4870d5
patch_sha=fc472e762767f3da60cfcb27ca0dcc38445c74610d19d38c7099c39b7da9ba94
expected_paths='pj_dialog_host/src/panel_engine.cpp'
title='Transform Editor creates a large exact Luau series while the browser main thread stays responsive'

case "$1" in
materialize)
  test -s "$evidence/verify.log"
  test "$(git rev-parse HEAD)" = "$a"
  git diff HEAD --exit-code
  mkdir "$saved"
  mv build-wasm-probe "$saved/acceptance"
  # The verified A artifact includes a standalone emrun.py under .emsdk.
  # Move it out of D's SDK install/cache path; the focused browser case serves via Node.
  mv .emsdk "$saved/emsdk"
  patch="$evidence/D-product.patch"
  base64 --decode "$here/panel-d.patch.b64" > "$patch"
  printf '%s  %s\n' "$patch_sha" "$patch" | sha256sum --check
  git apply --check --index --whitespace=error "$patch"
  git apply --index --whitespace=error "$patch"
  git diff --cached --check "$a"
  test "$(git diff --cached --name-only "$a")" = "$expected_paths"
  test "$(git write-tree)" = "$tree"
  cmd=(env GIT_AUTHOR_NAME='PlotJuggler candidate CI' GIT_AUTHOR_EMAIL=candidate-ci@example.invalid
       GIT_AUTHOR_DATE='2026-11-21T17:20:00Z' GIT_COMMITTER_NAME='PlotJuggler candidate CI'
       GIT_COMMITTER_EMAIL=candidate-ci@example.invalid GIT_COMMITTER_DATE='2026-11-21T17:20:00Z')
  commit=$("${cmd[@]}" git -c commit.gpgSign=false commit-tree "$tree" -p "$a" \
    -m 'Preserve startup registrations with shared parsed panel data')
  test "$commit" = "$d"
  git checkout --detach "$d"
  test "$(git rev-parse HEAD HEAD^{tree} HEAD^)" = "$(printf '%s\n' "$d" "$tree" "$a")"
  git diff HEAD --exit-code
  git cat-file commit "$d" > "$evidence/D-product.commit"
  printf 'baseline=%s\ncandidate=%s\ntree=%s\npatch_sha256=%s\nworkflow=%s\nrun=%s\n' \
    "$a" "$d" "$tree" "$patch_sha" "$GITHUB_SHA" "$GITHUB_RUN_ID" > "$evidence/D-identity.txt"
  ;;
pair)
  test "$(git rev-parse HEAD)" = "$d"
  test "$(git rev-parse HEAD^{tree})" = "$tree"
  git diff HEAD --exit-code
  # CMake locked toolchain mirrors the original acceptance configure. Retain the
  # actual profiling map, but neither acceptance run executes with a profiler.
  node scripts/package_wasm.mjs --compression-profile localized \
    --source build-wasm-probe/pj_app --output build-wasm-probe/deploy
  receipt() {
    # The immutable verifier's product-as-plan mode accepts exact D with no
    # comparator plan. Actual workflow SHA lives independently in D-identity.txt.
    python3 .ci-controller/packaging/localization/wasm_receipt.py "$1" \
      --role localized --source-repository "$GITHUB_REPOSITORY" --source-sha "$d" \
      --controller-sha "$d" --controller-root . --kind acceptance \
      --cache build-wasm-probe/CMakeCache.txt --package build-wasm-probe/deploy \
      --extra 'build-wasm-probe/pj_app/plotjuggler4*.symbols' --output "$evidence/D-acceptance-receipt.json"
  }
  receipt capture
  receipt verify
  cp build-wasm-probe/pj_app/plotjuggler4*.symbols "$evidence/"
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
  # Exact editors.spec.js and support inputs unchanged between A and D (the
  # checked one-file product-only diff contains no tests or toolchain pins).
  as=0 ds=0
  run_trial A "$saved/acceptance/deploy" 2>&1 | tee "$evidence/A.log" || as=$?
  run_trial D "$root/build-wasm-probe/deploy" 2>&1 | tee "$evidence/D.log" || ds=$?
  printf 'A=%s\nD=%s\n' "$as" "$ds" > "$evidence/pair-exits.txt"
  python3 "$here/evaluate_ab.py" "$evidence/A.json" "$evidence/D.json" "$as" "$ds"
  ;;
*) exit 2;;
esac
