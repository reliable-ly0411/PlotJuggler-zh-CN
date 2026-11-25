#!/usr/bin/env node
// SPDX-License-Identifier: MPL-2.0
// Pure script regression only. Does not emulate IFW or verify Windows restart.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,
  '../packaging/installer/packages/io.plotjuggler.application/meta/installscript.qs'), 'utf8');
const api = {};
vm.runInNewContext(source, api, {timeout: 1000});

let checks = 0;
function equal(actual, expected) {
  if (JSON.stringify(actual) !== JSON.stringify(expected))
    throw new Error(JSON.stringify({actual, expected}));
  checks++;
}
const languages = ['zh_CN', 'en_US', 'zh_TW'];
for (let source = 0; source < 3; source++) {
  for (let destination = 0; destination < 3; destination++) {
    if (source === destination) continue;
    const target = 'C:\\測試 space\\new target\\';
    const language = api.installerLanguageForIndex(destination, 3);
    equal(language, languages[destination]);
    equal(api.restartArguments(['setup.exe','--lang',languages[source],
      '--offline-only','--root','old target','TargetDir=obsolete','--proxy','http://localhost:8080'],
      language,target),
      ['--lang',language,'--offline-only','--root',target,'--proxy','http://localhost:8080','TargetDir='+target]);
  }
}
for (const locale of ['zh_TW','zh-Hant-TW','zh_HK','zh_MO','ZH_tw']) {
  equal(api.installerLanguageIndex(locale,3),2);
  equal(api.installerLanguageIndex(locale,2),locale.startsWith('zh') ? 0 : 1);
}
for (const locale of ['zh_CN','zh-Hans-CN','zh_SG','zh']) equal(api.installerLanguageIndex(locale,3),0);
for (const locale of ['en_US','de_DE','']) equal(api.installerLanguageIndex(locale,3),1);
for (let index=0; index<3; index++) equal(api.installerLanguageForIndex(index,3),languages[index]);
equal(api.installerLanguageForIndex(2,2),'en_US');
equal(api.installerLanguageIndex('en_US',2),1);
equal(api.installerLanguageIndex('zh_CN',2),0);
equal(api.installerLanguageIndex('zh_TW',2),0);
equal(api.installerLanguageForIndex(-1,3),'en_US');
equal(api.restartArguments(['setup.exe','--lang=en_US','-t=old','--','literal'], 'zh_TW','new'),
      ['--lang','zh_TW','-t=new','--','literal','TargetDir=new']);

console.log(`${checks} pure installer-language assertions passed; Windows GUI remains untested.`);
