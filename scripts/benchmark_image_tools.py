# SPDX-License-Identifier: MPL-2.0
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

p=argparse.ArgumentParser()
p.add_argument('--tools',required=True)
p.add_argument('--runtime',required=True)
p.add_argument('--out',required=True)
a=p.parse_args()
artifact=Path(a.tools).resolve()
out=Path(a.out).resolve()
out.mkdir(parents=True,exist_ok=True)
runtime=Path(a.runtime).resolve()
inputs=json.loads(next(artifact.rglob('inputs.json')).read_text(encoding='utf-8'))
env=dict(os.environ)
for key in list(env):
    if key.upper() in {'PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH',
                       'QML2_IMPORT_PATH','QML_IMPORT_PATH','QT_QPA_PLATFORM'}:
        env.pop(key)
system=Path(env.get('SystemRoot','C:/Windows'))
env['PATH']=str(runtime)+os.pathsep+str(system/'System32')+os.pathsep+str(system)
env['QT_QPA_PLATFORM']='windows'
env['QT_PLUGIN_PATH']=str(runtime)
env['QT_QPA_PLATFORM_PLUGIN_PATH']=str(runtime/'platforms')
exes={label:next(artifact.rglob('image_bench_'+label+'.exe')) for label in ('zh3','zh4')}
reports=[]
ids=[1,26,52,93]
for language in ('zh_CN','en_US'):
    for cache in ('warm','clear'):
        for repeat in range(4):
            order=ids[repeat:]+ids[:repeat]
            for label in (('zh3','zh4') if repeat%2==0 else ('zh4','zh3')):
                path=out/f'{language}-{cache}-{repeat}-{label}.json'
                result=subprocess.run([str(exes[label]),'--out',str(path),'--language',language,
                    '--cache',cache,'--ids',','.join(map(str,order)),'--rounds','12'],
                    cwd=runtime,env=env,capture_output=True,timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                assert result.returncode==0,(label,result.returncode,result.stderr.decode(errors='replace'))
                report=json.loads(path.read_text(encoding='utf-8'))
                assert report['qt']=='5.15.2' and len(report['samples'])==48
                report.update({'repeat':repeat,'first_id':order[0]})
                reports.append(report)
                print(json.dumps({'language':language,'cache':cache,'repeat':repeat,'version':label,
                    'first_render_ms':report['first_process_image_ms'],
                    'peak_working_set_bytes':report['peak_working_set_bytes']}),flush=True)
summary={'protocol':'Identical MSVC Release/C++17/Qt5.15.2 harness; exact pinned localizedMeme and image resource inputs',
         'inputs':{'baseline':inputs['baseline'],'candidate':inputs['candidate']},
         'harness_executable_sha256':{v:hashlib.sha256(p.read_bytes()).hexdigest() for v,p in exes.items()},
         'reports':reports,'limitations':['No OS file-cache flush or reboot',
             'Render timing excludes QWidget display, PNG encoding and disk export',
             'Fresh-process first render includes first catalog parse',
             'Round-robin warm condition is primed, but Qt may evict images from its cache',
             'Peak working set is for the isolated harness, not the full application']}
(out/'render-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('32 fresh-process runs and 1536 measured image render samples completed.',flush=True)
