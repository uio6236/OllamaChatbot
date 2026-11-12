/* 수동 Edge 헤드리스 검증. Node 22+ 내장 CDP/WebSocket만 사용한다. */
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const origin = 'http://127.0.0.1:8002';
const output = path.join(os.tmpdir(), 'hope_dev_ui_browser.json');
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'hope-dev-ui-edge-'));
const executable = process.env.BROWSER_EXE || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const browser = spawn(executable, ['--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1', `--user-data-dir=${profile}`, origin], {windowsHide:true, stdio:'ignore'});
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket, id=0;
const pending=new Map(), errors=[], requests=[], records=[];
async function waitUntil(check, timeout=65000){const end=Date.now()+timeout;while(Date.now()<end){if(await check())return;await delay(150);}throw new Error('브라우저 검증 대기 시간 초과');}
function rpc(method, params={}) {return new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});socket.send(JSON.stringify({id:key,method,params}));});}
async function evaluate(expression){const result=await rpc('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
async function ready(){await waitUntil(()=>evaluate(`!document.getElementById('question').disabled`));}
async function debug(){return JSON.parse(await evaluate(`document.getElementById('debug').textContent`));}
async function ask(message){await evaluate(`document.getElementById('question').value=${JSON.stringify(message)};document.getElementById('chatForm').requestSubmit();`);await ready();const data=await debug();assert.equal(data.ok,true);return data;}
async function main(){
 await waitUntil(()=>fs.existsSync(path.join(profile,'DevToolsActivePort')),15000);
 const port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];
 const pages=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 const page=pages.find(page=>page.type==='page'&&page.url.startsWith(origin));assert.ok(page,'로컬 페이지 연결');
 socket=new WebSocket(page.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 socket.onmessage=event=>{const data=JSON.parse(event.data);if(data.id){const task=pending.get(data.id);pending.delete(data.id);if(data.error)task.reject(new Error(JSON.stringify(data.error)));else task.resolve(data.result);}else if(data.method==='Runtime.exceptionThrown'){errors.push(data.params);}else if(data.method==='Network.requestWillBeSent'){requests.push(data.params.request);}};
 await rpc('Runtime.enable');await rpc('Network.enable');
 await rpc('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 await waitUntil(()=>evaluate(`document.getElementById('member').options.length===5`));
 const cases=[['additional','국민연금','1,200,000원',1001],['refund','연금저축','300,000원',1002],['rent','월세','0원',1003],['sme','중소기업 감면','1,000,000원',1004]];
 for(const [member,topic,amount,prediction] of cases){
   await evaluate(`document.getElementById('member').value=${JSON.stringify(member)};document.getElementById('member').dispatchEvent(new Event('change'));`);
   await ready();const briefing=await debug();assert.equal(briefing.ok,true);assert.equal(briefing.request.path,'/internal/recommendations');assert.equal(briefing.request.body.taxResult.predictionId,prediction);
   assert.equal(await evaluate(`document.querySelectorAll('#messages .bubble').length`),1);
   assert.equal(await evaluate(`document.getElementById('messages').scrollTop`),0);
   const first=await ask(`${topic} 공제 금액은 얼마인가요?`);assert.ok(first.response.answer.includes(amount));assert.equal(first.request.body.taxResult.predictionId,prediction);assert.equal(first.request.body.history.length,1);
   const method=await ask(`${topic} 공제는 어떻게 계산하나요?`);assert.equal(method.response.status,'ANSWERED');assert.equal(method.request.body.history.length,3);
   assert.ok((await evaluate(`document.getElementById('callInfo').textContent`)).includes('확인 불가'));
   records.push({member,briefing,first,method});fs.writeFileSync(output,JSON.stringify({records},null,2));
   console.log(JSON.stringify({member,briefing:briefing.httpStatus,followup:first.httpStatus,method:method.httpStatus,historyReset:true}));
 }
 for(let n=0;n<6;n++)await ask('환급액과 공제 내역을 알려주세요.');
 const last=await debug();assert.equal(last.request.body.history.length,10);assert.ok(last.request.body.history.reduce((n,m)=>n+m.content.length,0)<=12000);
 await ask('<img src=x onerror="window.unsafeExecuted=true">');
 assert.equal(await evaluate(`document.querySelectorAll('#messages img').length`),0);
 assert.equal(await evaluate(`window.unsafeExecuted===true`),false);
 await rpc('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
 await evaluate(`document.getElementById('question').value='서버 연결 오류 확인';document.getElementById('chatForm').requestSubmit();`);await ready();
 assert.ok((await evaluate(`document.querySelector('#messages .error').textContent`)).includes('개발 서버에 연결할 수 없습니다'));
 await rpc('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
 await evaluate(`document.getElementById('member').value='';document.getElementById('member').dispatchEvent(new Event('change'));`);
 assert.equal(await evaluate(`document.getElementById('question').disabled`),true);
 assert.ok((await evaluate(`document.getElementById('historyInfo').textContent`)).includes('0개'));
 await evaluate(`document.getElementById('member').value='rent';document.getElementById('member').dispatchEvent(new Event('change'));`);await ready();
 const screenshot=await rpc('Page.captureScreenshot',{format:'png'});const screenshotPath=path.join(os.tmpdir(),'hope_dev_ui.png');fs.writeFileSync(screenshotPath,Buffer.from(screenshot.data,'base64'));
 assert.equal(errors.length,0);assert.ok(requests.every(request=>!Object.keys(request.headers).some(key=>key.toLowerCase()==='x-chatbot-token')));assert.ok(requests.every(request=>!request.url.includes('/internal/')));
 const result={records,historyCap:true,selectionReset:true,xssTextOnly:true,offlineErrorMessage:true,noBrowserAuthHeader:true,noBrowserInternalApi:true,jsErrors:errors.length,screenshot:screenshotPath};fs.writeFileSync(output,JSON.stringify(result,null,2));console.log(JSON.stringify({passed:true,output,screenshot:screenshotPath}));
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{if(socket&&socket.readyState===1){try{await rpc('Browser.close');}catch{}socket.close();}browser.kill();});
