# OpenSSL Windows build-information overlay

This downstream recipe is exported as `openssl/3.6.5@plotjuggler/stable`, rather
than impersonating the Conan Center revision. The original CCI reference was
`openssl/3.6.5#3c1311f37543e7140f33fe5989f315c2`. Its recipe SHA256 was
`52172133a1415ab037dc10f55ac0dd6075378d739ad91193c778a0b2c6728d39`;
the unchanged conandata SHA256 is
`cfc6ffd2700379534bb7603bee2e12a0d270f3f27f904f88a3e6b3ea719a8f10`.
The original Conan.io MIT notice is retained. OpenSSL itself retains its
Apache-2.0 license and the exact official source archive pinned in conandata.

On Windows only, before compilation, the recipe checks and changes the single
`mkbuildinf.pl` assignment that emits compiler flags. Public compiler information
becomes `compiler: information not available`; all actual compiler options remain
unchanged and belong in private build records. This is a downstream source change,
not a binary edit or a claim that OpenSSL 3.6.5 already provides a new option.

The host overlay profile also selects a fixed product-specific `openssldir`.
It does not create that system directory or change user/global OpenSSL settings.
Runtime configuration, explicit CA use and affected TLS connections require
validation after rebuilding the actual static-library consumers.

The Windows/MSVC toolchain also clears the environment `LDFLAGS` override.
Extra link flags remain additive through the generated Conan target's `lflags`;
OpenSSL's inherited `/nologo /debug` defaults therefore remain active. This fixes
missing provider PDBs during `install_sw` when `/Brepro` is supplied. FIPS and
PDB installation are not disabled. The isolated two-cache build still has to
establish actual DLL reproducibility and path privacy.

The proposed recipe revision was obtained by an isolated Conan 2.33 export.
The Windows workflow uses Conan 2.34 and must reproduce the exact locked export
reference before graph resolution or compilation. A mismatch stops the build.
The 22 exact host references, their package IDs and mandatory Build statuses
remain checked. A matching export alone does not establish successful dependency
builds, plugin identities, package privacy, TLS behavior or source/license delivery.
