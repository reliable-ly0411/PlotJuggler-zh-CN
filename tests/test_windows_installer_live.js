const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const template=fs.readFileSync(__dirname+'/../scripts/windows_installer_live.qs.in','utf8');
for (let stage=0;stage<4;stage++) {
  const clicks=[], observations=[];
  const data={log:'log.jsonl',powershell:'powershell.exe',targets:['original','original','original'],changedTargets:['new one','new two']};
  const target={windowTitle:'Custom title',description:{text:'Custom description'},targetDirectory:{text:'original',setText(x){this.text=x;values.TargetDir=x}}};
  const page={language:{currentIndex:stage%2?1:0}};
  const values={UILanguage:stage%2?'en_US':'zh_CN',TargetDir:'original'};
  const context={
    installer:{fileExists:()=>stage>0,readFile:()=>Array(stage).fill('{"kind":"before-switch"}').join('\n'),value:key=>values[key],execute:(program,args)=>{observations.push(args);return ['',0]}},
    gui:{pageById:()=>({title:'Welcome'}),findChild:()=>({text:'Welcome'}),defaultButtonText:()=> 'Next',pageWidgetByObjectName:name=>name==='DynamicTargetWidget'?target:page,clickButton:(...args)=>clicks.push(args),rejectWithoutPrompt:()=>clicks.push(['reject'])},
    QInstaller:{Introduction:0},buttons:{NextButton:1,BackButton:0,CancelButton:4},
  };
  vm.createContext(context);vm.runInContext(template.replace('__PROBE_CONFIG__',JSON.stringify(data)),context);
  const controller=new context.Controller();
  controller.IntroductionPageCallback();
  if(stage>=2){assert.deepEqual(clicks,[['reject']]);continue;}
  controller.DynamicLanguageWidgetCallback();
  controller.DynamicTargetWidgetCallback();
  controller.DynamicLanguageWidgetCallback();
  assert.deepEqual(clicks,[[1,250],[1,250],[0,250],['applyLanguage',250]]);
  assert.equal(target.targetDirectory.text,data.changedTargets[stage]);
  assert.equal(page.language.currentIndex,stage===0?1:0);
  assert.equal(observations.length,4);
  values.TargetDir='unexpected existing directory';
  clicks.length=0;
  controller.IntroductionPageCallback();
  assert.deepEqual(clicks,[['reject']]);
}
console.log('Controller mock callbacks: both switches, final reject and target guard passed; not native GUI evidence.');
