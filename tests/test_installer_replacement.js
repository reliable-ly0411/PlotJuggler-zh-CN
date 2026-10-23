// SPDX-License-Identifier: MPL-2.0
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), zlib = require('node:zlib');
const root = path.join(__dirname, '..');
const helper = fs.readFileSync(path.join(root, 'packaging/installer/replacement_guard.ps1'));
const encoded = zlib.gzipSync(helper).toString('base64');
const source = fs.readFileSync(path.join(root, 'packaging/installer/packages/io.plotjuggler.application/meta/installscript.qs'), 'utf8').replace('__PJ_REPLACEMENT_HELPER_GZIP__', encoded);
function run(options = {}) {
  const events = [], logs = [];
  let lastCommand = '';
  let exists = options.exists !== false;
  let target = "C:/test's @safe@ 中文";
  const context = {
    console: {log: line => logs.push(line)},
    QInstaller: {ComponentSelection: 3},
    QMessageBox: {Yes: 1, No: 2, question: () => {events.push('confirm'); return options.decline ? 2 : 1}, warning: () => events.push('warning')},
    qsTranslate: (_, text) => text,
    gui: {rejectWithoutPrompt: () => events.push('quit')},
    installer: {
      value: () => target,
      fileExists: () => exists,
      environmentVariable: () => 'C:/Windows',
      execute: (_, args) => {
        events.push('execute');
        assert.equal(args.at(-2), '-EncodedCommand');
        assert.ok(!args.at(-1).includes('@')); // IFW substitution cannot damage transport.
        assert.ok(args.join(' ').length < 30000, 'Windows command-line limit margin');
        const command = Buffer.from(args.at(-1), 'base64').toString('utf16le');
        lastCommand = command;
        assert.ok(command.includes("-TargetPath 'C:/test''s @safe@ 中文'"));
        const packed = /FromBase64String\('([^']+)'\)/.exec(command)[1];
        assert.deepEqual(zlib.gunzipSync(Buffer.from(packed, 'base64')), helper);
        if (options.startThrows) throw Error('private-error');
        if (!options.residual) exists = false;
        if (options.targetChanged) target = 'different';
        return options.result ?? ['PJ_REPLACEMENT_OK\r\n', 0];
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  context.Component.prototype.componentSelectionPageEntered();
  return {events, logs, context, lastCommand};
}
assert.deepEqual(run({exists:false}).events, []); // Fresh install unchanged.
assert.deepEqual(run({decline:true}).events, ['confirm','quit']);
assert.deepEqual(run().events, ['confirm','execute']);
for (const failure of [{startThrows:true}, {result:[]}, {result:['PJ_REPLACEMENT_OK',1]},
                       {result:['PJ_REPLACEMENT_FAILED:wait',0]}, {residual:true}, {targetChanged:true}]) {
  const result = run(failure);
  assert.deepEqual(result.events, ['confirm','execute','warning','quit']);
  assert.ok(!result.logs.join(' ').includes('private-error'));
  // A repeated page signal can never silently retry a destructive operation.
  for (const targetStillExists of [true, false]) {
    result.context.installer.fileExists = () => targetStillExists;
    result.context.Component.prototype.componentSelectionPageEntered();
    assert.equal(result.events.at(-1), 'quit');
    assert.equal(result.context.replacementBlocked, true);
    assert.equal(result.events.filter(event => event === 'execute').length, 1);
    assert.equal(result.events.filter(event => event === 'confirm').length, 1);
  }
}
console.log('Replacement slot: fresh, decline, startup/exit failures, residual, success and no retry passed');

// Execute the real compressed bootstrap with an empty target: identity must
// fail before registry enumeration or any destructive process can be started.
const cp = require('node:child_process');
const shell = process.platform === 'win32' ? 'powershell.exe' : 'pwsh';
const available = cp.spawnSync(shell, ['-NoProfile', '-Command', 'exit 0']);
if (!available.error && available.status === 0) {
  const command = run().lastCommand.replace("-TargetPath 'C:/test''s @safe@ 中文'", "-TargetPath ''");
  const result = cp.spawnSync(shell, ['-NoProfile', '-NonInteractive', '-EncodedCommand', Buffer.from(command, 'utf16le').toString('base64')], {encoding:'utf8', timeout:30000});
  assert.equal(result.status, 1);
  assert.equal(result.stdout.trim(), 'PJ_REPLACEMENT_FAILED:identity');
  console.log('Real encoded/gzip bootstrap rejects empty target before destructive work');
}
