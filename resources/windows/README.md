# Windows application icon

`plotjuggler.ico` is a mechanical rasterization of the existing
`resources/plotjuggler.svg` application logo, not a new external image.
The icon contains 16, 24, 32, 48, 64, 128 and 256 pixel entries. The RC file
embeds it as the first icon group so Explorer and shortcut `iconId=0` agree.

To regenerate with Inkscape and Pillow:

```sh
inkscape resources/plotjuggler.svg --export-type=png \
  --export-filename=/tmp/plotjuggler-icon.png --export-width=256 --export-height=256
python3 -c 'from PIL import Image; Image.open("/tmp/plotjuggler-icon.png").save("resources/windows/plotjuggler.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])'
```

The linked PE is checked by `scripts/verify_windows_application.py`, not inferred
from CMake settings. `--runtime` additionally requires redirected `--version`
and `--help` output. This does not claim an Explorer visual inspection.
