// SPDX-License-Identifier: MPL-2.0
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const template = fs.readFileSync(path.join(__dirname, '../scripts/windows_installer_upgrade.qs.in'), 'utf8');
const config = {target:'C:/isolated/target', tool:'C:/isolated/target/maintenancetool.exe', receipt:'C:/isolated/target/FIXTURE-RECEIPT.txt',
  userMenu:'C:/isolated/menu-user', allMenu:'C:/isolated/menu-all', desktop:'C:/isolated/desktop', temporary:'C:/isolated/tmp',
  oldUuid:'{11111111-1111-1111-1111-111111111111}', newUuid:'{22222222-2222-2222-2222-222222222222}',
  oldReceipt:'PJ-SYNTHETIC-OLD', newReceipt:'PJ-SYNTHETIC-NEW', group:'SyntheticFixtureGroup', mode:'replace', powershell:'powershell.exe', log:'C:/isolated/log.jsonl'};
function fixture(changes={}) {
  const probe = {...config, ...changes}, events=[], clicks=[];
  const values = {TargetDir:probe.target, ProductUUID:probe.newUuid, UserStartMenuProgramsPath:probe.userMenu, AllUsersStartMenuProgramsPath:probe.allMenu,
    StartMenuDir:probe.group, DesktopDir:probe.desktop, AllUsers:'false', RunProgram:''};
  let exists=true, receipt=probe.oldReceipt;
  const installer = {status:4, value:k=>values[k], environmentVariable:()=>probe.temporary,
    fileExists:()=>exists, readFile:()=>receipt, autoRejectMessageBoxes:()=>{},
    setMessageBoxAutomaticAnswer:(name, answer)=>{assert.equal(name,'existing.install'); assert.equal(answer,1)},
    installationFinished:{connect:()=>{}}, execute:(_,args)=>{
      assert.equal(args.at(-2),'-EncodedCommand'); assert.ok(!args.at(-1).includes('@'));
      const ps=Buffer.from(args.at(-1),'base64').toString('utf16le');
      assert.ok(ps.includes(probe.oldUuid)); assert.ok(!ps.includes('DisplayName'));
      const match=/\$data='((?:[^']|'')*)' \| ConvertFrom-Json/.exec(ps);
      events.push(JSON.parse(match[1].replace(/''/g,"'")));
      return ['',0];
    }};
  const context={installer, QInstaller:{Success:0,StartMenuSelection:5}, QMessageBox:{Yes:1}, console:{log:()=>{}},
    buttons:{NextButton:'next',CommitButton:'commit',FinishButton:'finish'},gui:{
      rejectWithoutPrompt:()=>clicks.push('quit'),clickButton:b=>clicks.push(b),pageById:()=>({}),
      findChild:()=>({text:probe.group}),pageWidgetByObjectName:()=>({targetDirectory:{text:values.TargetDir}})}};
  vm.createContext(context); vm.runInContext(template.replace('__UPGRADE_CONFIG__',JSON.stringify(probe)),context);
  const controller=new context.Controller();
  return {controller,values,events,clicks,installer,setExists:v=>exists=v,setReceipt:v=>receipt=v};
}
const f=fixture();
f.controller.IntroductionPageCallback(); f.controller.DynamicLanguageWidgetCallback(); f.controller.DynamicTargetWidgetCallback();
f.setExists(false); f.controller.ComponentSelectionPageCallback(); f.controller.StartMenuDirectoryPageCallback();
f.values.StartMenuDir=config.userMenu+'/'+config.group;
f.controller.ReadyForInstallationPageCallback();
f.installer.status=0; f.setExists(true); f.setReceipt(config.newReceipt); f.controller.installed(); f.controller.FinishedPageCallback();
assert.deepEqual(f.events.map(e=>e.kind),['introduction','target','components','start-menu','ready','installed','finished']);
assert.deepEqual(f.clicks.slice(-3),['commit','commit','finish']);
for (const mutate of [f=>f.values.TargetDir='C:/outside', f=>f.values.RunProgram='unexpected.exe', f=>f.values.AllUsers='true', f=>f.values.DesktopDir='C:/outside']) {
  const bad=fixture(); mutate(bad); assert.throws(()=>bad.controller.IntroductionPageCallback()); assert.deepEqual(bad.clicks,['quit']);
}
for (const mode of ['replace','refuse-duplicate']) {
  const bad=fixture({mode}); bad.values.StartMenuDir=config.userMenu+'/'+config.group;
  assert.throws(()=>bad.controller.ReadyForInstallationPageCallback()); assert.deepEqual(bad.clicks,['quit']);
}
console.log('Synthetic upgrade Controller: scoped guards, exact buttons, success and refusal mocks passed; not native IFW evidence');
