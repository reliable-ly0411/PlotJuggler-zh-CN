# Browser Chinese font

Noto Sans SC, SIL Open Font License 1.1 (see `OFL.txt`).
Source: notofonts/noto-cjk at `f8d157532fbfaeda587e826d4cd5b21a49186f7c`,
`Sans/SubsetOTF/SC/NotoSansSC-Regular.otf`.
Source SHA-256: `faa6c9df652116dde789d351359f3d7e5d2285a2b2a1f04a2d7244df706d5ea9`.

Regenerate with `python3 scripts/make_cjk_font_subset.py SOURCE.otf` after
changing Chinese catalogs. The subset includes both catalogs, GB2312 level-1
characters and Chinese punctuation. It is embedded only in the browser build,
where system Chinese fonts are unavailable. It remains counted by the unchanged
WASM package size budget.
