const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const template = fs.readFileSync(__dirname + '/../scripts/windows_installer_live.qs.in', 'utf8');

function fixture(stage, hasComponent = true) {
  const clicks = [], observations = [];
  const data = {log: 'log.jsonl', powershell: 'powershell.exe', targets: ['original', 'original', 'original'], changedTargets: ['new one', 'new two']};
  const values = {UILanguage: stage % 2 ? 'en_US' : 'zh_CN', TargetDir: 'original'};
  const target = {windowTitle: 'Custom title', description: {text: 'Custom description'}, targetDirectory: {text: 'original', setText(x) { this.text = x; values.TargetDir = x; }}};
  const page = {language: {currentIndex: stage % 2 ? 1 : 0}};
  let loaded = false, lookups = 0;
  const context = {
    installer: {
      componentByName: name => {
        assert.equal(name, 'io.plotjuggler.application');
        ++lookups;
        return loaded && hasComponent ? {value: key => key === 'DisplayName' ? 'name' : 'description'} : null;
      },
      environmentVariable: () => '/tmp', fileExists: () => stage > 0,
      readFile: () => Array(stage).fill('{"kind":"before-switch"}').join('\n'), value: key => values[key],
      execute: (program, args) => {
        observations.push(Buffer.from(args[3], 'base64').toString('utf16le'));
        return ['', 0];
      }
    },
    gui: {pageById: () => ({title: 'Welcome'}), findChild: () => ({text: 'Welcome'}), defaultButtonText: () => 'Next',
      pageWidgetByObjectName: name => name === 'DynamicTargetWidget' ? target : page,
      clickButton: (...args) => clicks.push(args), rejectWithoutPrompt: () => clicks.push(['reject'])},
    QInstaller: {Introduction: 0}, buttons: {NextButton: 1, BackButton: 0, CancelButton: 4}
  };
  vm.createContext(context);
  vm.runInContext(template.replace('__PROBE_CONFIG__', JSON.stringify(data)), context);
  return {controller: new context.Controller(), clicks, observations, values, target, page, data,
    loadComponents: () => { loaded = true; }, lookupCount: () => lookups};
}
function kinds(f) {
  return f.observations.map(command => {
    const match = command.match(/"kind":"([^"]+)"/);
    assert.ok(match, 'Observer must record an event kind');
    return match[1];
  });
}

for (let stage = 0; stage < 3; ++stage) {
  const f = fixture(stage);
  f.controller.IntroductionPageCallback();
  assert.equal(f.lookupCount(), 0, 'Introduction must not inspect the not-yet-loaded component tree');
  assert.deepEqual(f.clicks, [[1, 250]]);
  f.loadComponents(); // IFW loads components when Introduction's Next validates.
  f.controller.DynamicLanguageWidgetCallback();
  assert.equal(f.lookupCount(), 1);
  if (stage === 2) {
    assert.deepEqual(f.clicks, [[1, 250], [0, 250]]);
    f.controller.IntroductionPageCallback();
    assert.deepEqual(f.clicks, [[1, 250], [0, 250], [4, 250]]);
    assert.deepEqual(kinds(f), ['introduction', 'component-metadata', 'finished']);
    continue;
  }
  f.controller.DynamicTargetWidgetCallback();
  f.controller.DynamicLanguageWidgetCallback();
  assert.deepEqual(f.clicks, [[1, 250], [1, 250], [0, 250], ['applyLanguage', 250]]);
  assert.deepEqual(kinds(f), ['introduction', 'component-metadata', 'target-before-edit', 'target-edited', 'before-switch']);
  assert.equal(f.lookupCount(), 1, 'Returning to language must not duplicate metadata');
  assert.equal(f.target.targetDirectory.text, f.data.changedTargets[stage]);
  assert.equal(f.page.language.currentIndex, stage === 0 ? 1 : 0);
  f.values.TargetDir = 'unexpected existing directory';
  f.clicks.length = 0;
  f.controller.IntroductionPageCallback();
  assert.deepEqual(f.clicks, [['reject']]);
}
for (let stage = 0; stage < 3; ++stage) {
  const f = fixture(stage, false);
  f.controller.IntroductionPageCallback();
  f.loadComponents();
  f.controller.DynamicLanguageWidgetCallback();
  assert.deepEqual(f.clicks, [[1, 250], ['reject']], 'Missing component must stop navigation and switching');
  assert.deepEqual(kinds(f), ['introduction', 'unexpected-component']);
}
{
  const f = fixture(2);
  f.controller.DynamicTargetWidgetCallback();
  assert.deepEqual(f.clicks, [['reject']]);
  assert.deepEqual(kinds(f), ['unexpected-page']);
}
{
  const f = fixture(3);
  f.controller.IntroductionPageCallback();
  assert.deepEqual(f.clicks, [['reject']]);
  assert.deepEqual(kinds(f), ['unexpected-target']);
  assert.equal(f.lookupCount(), 0);
}
console.log('Controller mocks: component lifecycle, both switches, final Back/Cancel and fail-closed guards passed; not native GUI evidence.');
