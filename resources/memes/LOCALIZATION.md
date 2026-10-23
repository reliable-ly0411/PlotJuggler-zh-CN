# Original 4.x meme localization

This catalog is separate from the eight additional Chinese two-panel jokes.
It records all 37 original slots, including incomplete slots, and does not modify
the 37 English JPEG originals. Only pixel-reviewed entries are eligible for the
Chinese pool. A missing translation never silently becomes an English image.

Assets marked `source_3x_id` reuse Chinese assets from this same repository's
v3.18.0-zh.4 release. Full images are loaded directly; existing caption atlas
patches use the original Qt image compositor without repainting caption pixels.
New 4.x assets are text-localization image edits of the corresponding originals,
not newly invented replacement jokes. Source hashes identify inputs, not visual
acceptance of composed results.

`zh_CN.json` is the per-image review record: source hash, original and translated
caption, provenance, pixel review, exceptions and blocked status. Source-photo
watermarks and product names remain. Screenshot UI labels in meme 36 are translated alongside its main and small-sign
captions. Product names, real data identifiers, numbers and units are retained.

Attribution and rights: these images derive from the existing upstream meme
collection. Existing visible attribution is preserved. This localization does
not assert a new license to underlying films, cartoons, photographs or marks.
The repository's source-code license does not by itself establish rights to
those third-party depictions.

Validation: header-only loader and copied Qt compositor compiled with Qt 6.11.1;
all current translated variants exported successfully offscreen and inspected
individually. This is Linux pixel validation, not a Windows GUI acceptance run.
