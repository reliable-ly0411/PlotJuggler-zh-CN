#!/usr/bin/env bash
set -euo pipefail
repo=reliable-ly0411/PlotJuggler-zh-CN
controller=ea8dd1ebdabde31baf2c44f5743f6a2e52d50d63
helper=4c1ddc674097a5ab7391368050303208f99a6c72
d=2e9235ef1575551f4fa14c84ce150301e4022bcd
tree=483bb27b54c929697295978fc66a1c59da4870d5
run=44938040959
job=136948897517
evidence="$PWD/replay-evidence"
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$evidence" validation-receipts build-wasm-probe/pj_app
test "$GITHUB_REPOSITORY" = "$repo"
test "$(git -C .replay-controller rev-parse HEAD)" = "$GITHUB_SHA"
test "$(git -C .ci-controller rev-parse HEAD)" = "$helper"
bash "$here/ab.sh" source
download() {
  local id="$1" name="$2" digest="$3" zip="$4" meta="$5"
  gh api "repos/$repo/actions/artifacts/$id" > "$meta"
  jq -e --arg name "$name" --arg digest "sha256:$digest" --arg sha "$controller" --argjson run "$run" --argjson id "$id" \
    '.id == $id and .name == $name and .expired == false and .digest == $digest
     and .workflow_run.id == $run and .workflow_run.head_sha == $sha' "$meta"
  gh api "repos/$repo/actions/artifacts/$id/zip" > "$zip"
  printf '%s  %s\n' "$digest" "$zip" | sha256sum --check
}
package="$RUNNER_TEMP/pj71-D-package.zip"
proof="$RUNNER_TEMP/pj71-D-evidence.zip"
download 14720507779 pj71-luau-D-2e9235ef-acceptance-1 \
  c1032acce412409df1e0238b6b462a3e60282397eb6839002c34faa43354113a "$package" "$evidence/D-package-metadata.json"
download 14720647644 pj71-wasm-artifact-replay-firefox-1 \
  a5ec6b017069d3d08ccf0009a1d1aa6c4980c6cddcc194f6bfec02d44ea43a3b "$proof" "$evidence/D-evidence-metadata.json"
unzip -q "$package" 'build-wasm-probe/deploy/*'
unzip -p "$package" replay-evidence/D-acceptance-receipt.json > validation-receipts/acceptance.json
unzip -p "$package" replay-evidence/D-identity.txt > "$evidence/D-original-identity.txt"
unzip -p "$proof" D-acceptance-receipt.json | cmp - validation-receipts/acceptance.json
unzip -p "$proof" D-identity.txt | cmp - "$evidence/D-original-identity.txt"
unzip -p "$proof" D.json > "$evidence/D-original-gate-44938040959.json"
unzip -p "$proof" plotjuggler4.js.symbols > build-wasm-probe/pj_app/plotjuggler4.js.symbols
test -s build-wasm-probe/pj_app/plotjuggler4.js.symbols
cp validation-receipts/acceptance.json "$evidence/D-acceptance-original.json"
grep -Fx "candidate=$d" "$evidence/D-original-identity.txt"
grep -Fx "tree=$tree" "$evidence/D-original-identity.txt"
grep -Fx "workflow=$controller" "$evidence/D-original-identity.txt"
grep -Fx "run=$run" "$evidence/D-original-identity.txt"
printf 'artifact_run=%s\nartifact_job=%s\nartifact_controller=%s\n' "$run" "$job" "$controller" \
  > "$evidence/D-original-producer.txt"
python3 .ci-controller/packaging/localization/wasm_receipt.py verify \
  --role localized --source-repository "$repo" --source-sha "$d" --controller-sha "$d" \
  --controller-root . --kind acceptance --package build-wasm-probe/deploy \
  --extra 'build-wasm-probe/pj_app/plotjuggler4*.symbols' --output validation-receipts/acceptance.json \
  | tee "$evidence/D-artifact-verify.log" "$evidence/verify.log"
