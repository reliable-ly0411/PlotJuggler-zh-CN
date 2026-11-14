# SPDX-License-Identifier: MPL-2.0
"""Audit the frozen baf7d621 product, not the validation-control commit.

Only the final audit catalog is installed AFTER all identities, source inputs,
Conan toolchain and adversarial probes pass. No binary bytes are rewritten.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

MANIFEST = Path(__file__).resolve().parents[1] / 'tests/data/frozen-baf7d621.json'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()

def verify_source(root, manifest, initial=False):
    require(git(root, 'rev-parse', 'HEAD') == manifest['source'], 'Wrong product commit')
    require(git(root, 'rev-parse', 'HEAD^{tree}') == manifest['tree'], 'Wrong product tree')
    require(git(root, 'show', '-s', '--format=%ct', 'HEAD') == str(manifest['epoch']), 'Wrong product epoch')
    for relative, expected in manifest['source_files'].items():
        require(digest((root / relative).read_bytes()) == expected, 'Source input differs: ' + relative)
    if initial:
        require(not git(root, 'diff', 'HEAD', '--name-only'), 'Dirty source before building')

def exact_policy(root, payload, manifest):
    records=json.loads((root/'tests/data/public-build-records.json').read_text())
    # No inherited local identity or timestamp-equivalent fingerprint for these DLLs.
    records['public_ci_source_records']={}
    for name, item in manifest['dlls'].items():
        data=(payload/name).read_bytes()
        require(len(data)==item['bytes'] and digest(data)==item['sha256'], 'Exact DLL mismatch: '+name)
        records.get('local_reviewed_exact_sha256',{}).pop(name,None)
        records['public_ci_source_records'][name]={
            'observed_plugin_sha256':item['sha256'], 'nul_terminated_literals':[],
            'content_fingerprint':{'sha256':''}, 'source_commit':manifest['source'],
            'review_run':manifest['review_run'], 'review_artifact':manifest['review_artifact']}
    data=(payload/'ToolboxMosaico.dll').read_bytes()
    for item in manifest['qrc_structs']:
        start=item['dll_offset']; blob=data[start:start+item['bytes']]
        require(digest(blob)==item['sha256'], 'QRC structure mismatch')
        require(all(int.from_bytes(blob[i+14:i+22],'big')==manifest['epoch']*1000
                    for i in range(0,len(blob),22)), 'QRC timestamp differs from fixed source epoch')
    return records

def verify_toolchain(graph, manifest):
    nodes=graph['graph']['nodes'].values()
    hosts=[n for n in nodes if n.get('context')=='host' and n.get('ref')]
    require(bool(hosts),'No host dependency graph')
    for n in hosts:
        s=n.get('settings',{})
        require(s.get('os')=='Windows' and s.get('arch')=='x86_64' and
                s.get('compiler')=='msvc' and str(s.get('compiler.version'))=='194' and
                s.get('build_type')=='Release', 'Wrong host toolchain: '+str(n.get('ref')))

def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--initial',action='store_true')
    ap.add_argument('--payload',type=Path)
    ap.add_argument('--graph',type=Path)
    ap.add_argument('--out',type=Path)
    a=ap.parse_args(); root=a.source.resolve(); m=json.loads(MANIFEST.read_text())
    verify_source(root,m,a.initial)
    if a.initial:
        print('PASS: frozen source/tree/epoch/input hashes'); return
    require(a.payload is not None and a.graph is not None and a.out is not None,'Missing audit arguments')
    require(not a.out.exists(),'Audit output already exists')
    for name in ('SOURCE_DATE_EPOCH','QT_RCC_SOURCE_DATE_OVERRIDE'):
        require(os.environ.get(name)==str(m['epoch']), 'Wrong '+name)
    graph=json.loads(a.graph.read_text(encoding='utf-8-sig')); verify_toolchain(graph,m)
    info=list(a.payload.rglob('BUILD-INFO.json'))
    require(len(info)==1,'Expected exactly one build identity')
    require(json.loads(info[0].read_text(encoding='utf-8-sig')).get('commit')==m['source'],'Wrong payload source')
    records=exact_policy(root,a.payload,m)
    sys.path.insert(0,str(root/'scripts'))
    from verify_public_binary_records import verify_payload
    probes=verify_payload(a.payload,records)
    require(len(probes)==3 and sum(len(x['negative_cases_rejected']) for x in probes)==24,'Incomplete adversarial coverage')
    report={'passed':True,'source':m['source'],'source_tree':m['tree'],'source_epoch':m['epoch'],
            'control_commit':git(Path(__file__).resolve().parents[1],'rev-parse','HEAD'),
            'review_run':m['review_run'],'review_artifact':m['review_artifact'],
            'review_archive_sha256':m['review_archive_sha256'],
            'graph_sha256':digest(a.graph.read_bytes()),'checks':probes,'qrc':m['qrc_structs']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    # Downstream existing package/secret/path gates consume the exact-only catalog.
    # Build and runtime tests already finished against the unmodified frozen tree.
    (root/'tests/data/public-build-records.json').write_text(json.dumps(records,indent=2)+'\n')
    print('PASS: frozen product identities, toolchain, epoch and 24 negative probes; audit catalog installed')

if __name__=='__main__':
    main()
