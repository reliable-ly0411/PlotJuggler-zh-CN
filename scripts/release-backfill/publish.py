#!/usr/bin/env python3
"""Append verified missing Linux packages; never replace or remove release assets."""
import hashlib,json,os,pathlib,urllib.request,urllib.parse
repo='reliable-ly0411/PlotJuggler-zh-CN'
tag=os.environ['SOURCE_TAG']; sha=os.environ['SOURCE_SHA']
api=f'https://api.github.com/repos/{repo}'
def request(url,data=None,method='GET',content_type='application/json'):
    headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    if data is not None:
        headers['Content-Type']=content_type
        if not isinstance(data,bytes): data=json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers,method=method),timeout=180) as r:
        return json.load(r)
assert request(api+'/git/ref/heads/release/backfill-zh-linux')['object']['sha']==os.environ['GITHUB_SHA'], 'Superseded packaging run must not publish'
ref=request(api+'/git/ref/tags/'+tag)['object']
if ref['type']=='tag': ref=request(ref['url'])['object']
assert ref['sha']==sha,ref
release=request(api+'/releases/tags/'+tag)
original={a['name']:(a['id'],a['size'],a.get('digest')) for a in release['assets']}
version=f'{tag[1:]}+upstream.3.17.2.apbin.1.g{sha[:12]}'
expected={f'PlotJuggler-{version}-aarch64.AppImage'} | {f'PlotJuggler-{version}-{d}-amd64.deb' for d in ['24.04','bookworm','trixie']}
files={p.name:p for p in pathlib.Path('artifacts').rglob('*') if p.is_file()}
assert set(files)==expected,(set(files),expected)
hashes={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files.items()}
for name,p in sorted(files.items()):
    if name in original:
        assert original[name][2]=='sha256:'+hashes[name],f'Existing asset differs: {name}'
        continue
    upload=release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(name)
    result=request(upload,p.read_bytes(),'POST','application/octet-stream')
    assert result['name']==name and result['size']==p.stat().st_size
    assert result.get('digest')=='sha256:'+hashes[name],result
    print('Uploaded',name,hashes[name],flush=True)
fresh=request(api+'/releases/tags/'+tag)
assets={a['name']:(a['id'],a['size'],a.get('digest')) for a in fresh['assets']}
assert all(assets.get(n)==v for n,v in original.items()),'An existing release asset changed'
assert all(assets[n][2]=='sha256:'+h for n,h in hashes.items())
marker='### Linux 补充发行包（原标签源码）'
if marker not in fresh['body']:
    text=f'\n\n{marker}\n\n新增 aarch64 AppImage，以及 Ubuntu 24.04、Debian 12 bookworm、Debian 13 trixie 的 amd64 DEB。源码为 `{sha}`，版本保持 `{version}`。\n\nDEB 的 Debian Version 使用 `3.18.0~zh.{tag.rsplit(".",1)[1]}` 前缀以保持先行版排序；程序内版本仍使用上述原始 SemVer。DEB 安装前须配置与发行版匹配的 [Apache Arrow 官方 APT 仓库](https://arrow.apache.org/install/)，然后使用 `sudo apt install ./对应文件.deb`，由 APT 安装包中声明的运行依赖。三个 DEB 不可跨发行版混装。aarch64 AppImage 适用于 ARM64 Linux，打包基线为 Ubuntu 22.04。\n\n已通过原标签翻译、版本、CTest，以及独立运行环境中的中英文界面与 ArduPilot BIN 验收。构建记录：[GitHub Actions]({os.environ["RUN_URL"]})。\n\n补充包 SHA256：\n'
    for name,h in sorted(hashes.items()): text+=f'\n- `{name}`：`{h}`'
    request(api+f'/releases/{release["id"]}',{'body':fresh['body']+text},'PATCH')
final=request(api+'/releases/tags/'+tag)
assert marker in final['body']
assert len(final['assets'])==7, len(final['assets'])
print(final['html_url']);print(json.dumps(hashes,indent=2))
