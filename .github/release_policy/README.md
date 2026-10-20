# Release-gated automation

Daily sync still merges only upstream Qt5 `main` into `zh-CN-dev`, preserves local translations/policy, and runs lightweight validation. Manual sync defaults to sync-only. Only a new formal matching 3.x GitHub release invokes the native seven-platform candidate workflow; experimental 3.999.x (PJ4 betas), prereleases and historical releases are excluded. The ledger uses normal non-force commits on `release-policy-state-pj3`; retries preserve the exact first recognized release ID/tag SHA and downstream patch baseline. Builds reconstruct released tag + local delta, never current upstream HEAD.

Manual `zh-release.yml` / `zh-windows.yml` / `zh-linux.yml` remain build-only, with no publisher. Image/native audit tools are manual. Original package/privacy/resource audits are unchanged. A successful native build is not a human GUI acceptance or authorization to publish. No new automatic publisher is enabled until source anchoring, version mapping, compatibility and final screenshot acceptance are established. Historical offline release-review helpers remain nonpublishing.

Activate matching policy on both `zh-CN-dev` and `zh-CN`; the detector deliberately fails closed if development lacks the reviewed policy. PJ4 workflow/source histories stay isolated, with their explicit manual candidate/promotion refs and human review gates.
