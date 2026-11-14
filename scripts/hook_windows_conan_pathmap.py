"""Experimental Conan 2 hook: exact recipe paths, never binary rewriting.

Inactive without an explicit profile policy digest. Install only in an isolated
probe CONAN_HOME. Passing Python tests is NOT proof of MSVC flag consumption.
"""
import hashlib
import json
import ntpath
import re
from pathlib import Path

POLICY_CONF = 'user.plotjuggler:pathmap_policy'
REFS_CONF = 'user.plotjuggler:pathmap_refs'


def policy_digest(refs):
    return hashlib.sha256(Path(__file__).read_bytes() + b'\0' +
                          json.dumps(sorted(refs), separators=(',', ':')).encode()).hexdigest()


def exact_ref(ref):
    """Avoid str(RecipeReference), which need not include its revision."""
    fields = [getattr(ref, n, None) for n in ('name', 'version', 'user', 'channel', 'revision')]
    name, version, user, channel, revision = fields
    # Conan RecipeReference.version is a Version object, not necessarily str.
    version = str(version) if version is not None else None
    for value in (name, version):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+', value):
            raise ValueError('missing or unsafe recipe identity')
    if bool(user) != bool(channel):
        raise ValueError('incomplete recipe namespace')
    if user:
        if any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+', x) for x in (user, channel)):
            raise ValueError('unsafe recipe namespace')
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{32}', revision):
        raise ValueError('recipe revision must be pinned')
    return f'{name}/{version}' + (f'@{user}/{channel}' if user else '') + f'#{revision}'


def root(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z]:[\\/][A-Za-z0-9_.\\/-]+', value):
        raise ValueError('mapping root must be a simple absolute Windows path')
    value = value.replace('/', '\\')
    if ntpath.normpath(value) != value or value.endswith('\\'):
        raise ValueError('mapping root must be normalized, not a drive root')
    return value.replace('\\', '/')


def identity(item, allowed):
    ref = exact_ref(item.ref)
    if ref not in allowed:
        raise ValueError(f'unreviewed recipe: {ref}')
    # Raw Conan package IDs include physical /pathmap flags in this project.
    # Preserve the semantic build identity, but not those cache-dependent flags.
    settings = item.settings.dumps()
    options = item.options.dumps()
    if not isinstance(settings, str) or not isinstance(options, str):
        raise ValueError('unavailable package settings/options')
    semantic = hashlib.sha256(json.dumps([ref, settings, options], separators=(',', ':')).encode()).hexdigest()
    return 'Z:/pj-conan-exact/' + semantic


def mapping_flags(conanfile, allowed):
    """Map actual directories, not guessed Conan cache tokens or wildcards."""
    entries = {}
    destinations = {}
    def add(source, target):
        source = root(source)
        key = source.casefold()
        if key in entries and entries[key] != (source, target):
            raise ValueError('conflicting mapping for one source root')
        if target in destinations and destinations[target] != key:
            raise ValueError('ambiguous package identity at distinct roots')
        entries[key] = (source, target)
        destinations[target] = key
    if getattr(conanfile, 'ref', None) is not None:
        own = identity(conanfile, allowed)
        source, build = root(conanfile.source_folder), root(conanfile.build_folder)
        if source.casefold() == build.casefold():
            add(source, own + '/source-build')
        else:
            add(source, own + '/source')
            add(build, own + '/build')
    for dep in conanfile.dependencies.host.values():
        # No binaries or headers are expected from a dependency without a package
        # folder. Require evidence instead of silently omitting it.
        add(dep.package_folder, identity(dep, allowed) + '/package')
    # Longest first. Actual MSVC precedence against the root fallback must still
    # be proved by the Windows probe before production activation.
    ordered = sorted(entries.values(), key=lambda p: (-len(p[0]), p[0].casefold()))
    return [f'/pathmap:{source}={target}' for source, target in ordered]


def pre_generate(conanfile):
    policy = conanfile.conf.get(POLICY_CONF, default=None)
    if policy is None:
        return
    # Root consumer keeps project fallback but still maps dependency headers.
    if conanfile.context != 'host':
        raise ValueError('experimental mapping does not authorize build-context recipes')
    if str(conanfile.settings.get_safe('os')) != 'Windows' or str(conanfile.settings.get_safe('compiler')) != 'msvc':
        return
    refs = conanfile.conf.get(REFS_CONF, check_type=list)
    if not refs or any(not isinstance(r, str) for r in refs) or len(set(refs)) != len(refs):
        raise ValueError('invalid reviewed recipe list')
    if policy != policy_digest(refs):
        raise ValueError('pathmap policy digest mismatch')
    confs = conanfile.conf.get('tools.info.package_id:confs', check_type=list)
    if POLICY_CONF not in confs or REFS_CONF not in confs:
        raise ValueError('pathmap policy must participate in package identity')
    exact = mapping_flags(conanfile, set(refs))
    updates = {}
    for field in ('tools.build:cflags', 'tools.build:cxxflags'):
        existing = conanfile.conf.get(field, check_type=list)
        if not existing or any(not isinstance(flag, str) for flag in existing):
            raise ValueError('missing existing deterministic/root fallback flags')
        if '/experimental:deterministic' not in existing or not any(flag.startswith('/pathmap:') and flag.endswith('=Z:/pj-conan') for flag in existing):
            raise ValueError('required root fallback or deterministic flag missing')
        updates[field] = exact + existing
    for field in ('tools.build:sharedlinkflags', 'tools.build:exelinkflags'):
        existing = conanfile.conf.get(field, default=None)
        if existing is None: continue
        if existing != ['/Brepro'] or field not in confs:
            raise ValueError('reviewed linker flags must participate in package identity')
    for field, value in updates.items():
        conanfile.conf.define(field, value)

def stable_mimalloc_banner(path):
    """Remove volatile diagnostic-banner macros before compilation, not in DLLs."""
    original = ', __DATE__, __TIME__);'
    replacement = ', "reproducible build", "time not recorded");'
    text = path.read_text(encoding='utf-8')
    if text.count(original) != 1:
        raise ValueError('unexpected pinned mimalloc options.c banner')
    path.write_text(text.replace(original, replacement), encoding='utf-8')


def pre_build(conanfile):
    policy = conanfile.conf.get(POLICY_CONF, default=None)
    if policy is None:
        return
    if conanfile.context != 'host' or str(conanfile.settings.get_safe('os')) != 'Windows':
        return
    if exact_ref(conanfile.ref) != 'mimalloc/2.2.4#dd236e6e0a2a1ef80cbc193d6f7f7090':
        return
    refs = conanfile.conf.get(REFS_CONF, check_type=list)
    if policy != policy_digest(refs) or exact_ref(conanfile.ref) not in refs:
        raise ValueError('unreviewed mimalloc banner policy')
    stable_mimalloc_banner(Path(conanfile.source_folder) / 'src' / 'options.c')
