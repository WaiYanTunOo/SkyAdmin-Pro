/** Admin page — hidden generator UI served at a secret path. */

import { Context } from "hono";
import { getCookie, setCookie } from "hono/cookie";
import { Env } from "../db";
import { adminSessionSalt } from "../env_secrets";
import { hmacSign } from "../signing";
import {
  isBlockedAttemptCount,
  loginBlockCutoffIso,
  readAttemptCount,
} from "../admin_security";

const SESSION_TTL = 86400 * 7; // 7 days
const CSRF_TTL = 3600; // 1 hour

function sessionKey(secret: string): string {
  return "skyadm_" + secret.slice(0, 8);
}

function csrfKey(secret: string): string {
  return "csrf_" + secret.slice(0, 8);
}

async function generateCsrfToken(adminPass: string, adminPath: string): Promise<string> {
  const ts = Math.floor(Date.now() / 1000).toString();
  const sig = await hmacSign(adminPass, adminPath + ":csrf:" + ts);
  return ts + "." + sig;
}

async function validateCsrfToken(token: string, adminPass: string, adminPath: string): Promise<boolean> {
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [ts, sig] = parts;
  const tsNum = parseInt(ts, 10);
  if (isNaN(tsNum)) return false;
  const now = Math.floor(Date.now() / 1000);
  if (now - tsNum > CSRF_TTL) return false;
  const expected = await hmacSign(adminPass, adminPath + ":csrf:" + ts);
  return sig === expected;
}

async function isValidSession(c: Context<{ Bindings: Env }>): Promise<boolean> {
  const cookieName = sessionKey(adminSessionSalt(c.env));
  const token = getCookie(c, cookieName);
  if (!token) return false;
  const expected = await hmacSign(c.env.ADMIN_PASS, c.env.ADMIN_PATH + ":session");
  return token === expected;
}

async function isIpBlocked(c: Context<{ Bindings: Env }>, ip: string): Promise<boolean> {
  const cutoff = loginBlockCutoffIso();
  const row = await c.env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM login_attempts WHERE ip = ? AND attempted_at > ?"
  ).bind(ip, cutoff).first<{ cnt: number }>();
  return isBlockedAttemptCount(readAttemptCount(row));
}

async function recordLoginAttempt(c: Context<{ Bindings: Env }>, ip: string): Promise<void> {
  await c.env.DB.prepare(
    "INSERT INTO login_attempts (ip) VALUES (?)"
  ).bind(ip).run();
  // Cleanup old entries (older than 1 hour)
  const cutoff = new Date(Date.now() - 3600 * 1000).toISOString();
  await c.env.DB.prepare(
    "DELETE FROM login_attempts WHERE attempted_at < ?"
  ).bind(cutoff).run();
}

function loginPage(adminPath: string, error?: string): string {
  const loginUrl = adminPath + "/login";
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SkyAdmin</title>
<style>
body{font-family:-apple-system,Helvetica,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#111827;color:#f9fafb}
.box{background:#1f2937;padding:32px;border-radius:16px;width:320px;text-align:center}
h2{margin:0 0 16px;font-size:18px}
input{width:100%;padding:12px;border:1px solid #374151;border-radius:10px;background:#111827;color:#f9fafb;font-size:16px;box-sizing:border-box;text-align:center;letter-spacing:4px}
button{margin-top:14px;width:100%;padding:12px;border:0;border-radius:10px;background:#2563eb;color:white;font-size:15px;font-weight:700}
button:active{background:#1d4ed8}
.err{color:#f87171;font-size:13px;margin-top:10px}
</style></head><body>
<div class="box">
<h2>SkyAdmin Pro</h2>
<form method="POST" action="${loginUrl}">
<input type="hidden" name="csrf_token" value="">
<input name="password" type="password" placeholder="Password" autofocus>
<button type="submit">Enter</button>
</form>
${error ? '<div class="err">' + error + '</div>' : ''}
</div></body></html>`;
}

const ADMIN_HTML_BUILDER = (adminPath: string, apiToken: string) => `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SkyAdmin Pro</title>
<style>
*{box-sizing:border-box}
body{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:680px;margin:0 auto;padding:16px;background:#111827;color:#f9fafb;-webkit-text-size-adjust:100%}
h1{font-size:20px;margin:0 0 4px} h2{font-size:16px;margin:22px 0 8px;color:#9ca3af}
.sub{color:#6b7280;font-size:12px;margin-bottom:16px}
label{font-weight:600;font-size:13px;display:block;margin:12px 0 5px;color:#d1d5db}
input,select{width:100%;padding:11px;border:1px solid #374151;border-radius:10px;background:#1f2937;color:#f9fafb;font-size:15px;-webkit-appearance:none}
button{margin-top:14px;width:100%;padding:13px;border:0;border-radius:10px;background:#2563eb;color:white;font-size:15px;font-weight:700}
button:active{background:#1d4ed8} button:disabled{background:#4b5563}
button.sm{width:auto;padding:7px 12px;font-size:12px;border-radius:8px;margin-top:0}
.gray{background:#374151;color:#e5e7eb;border:1px solid #4b5563}
.green{background:#059669}
.red{background:#dc2626}
.out{margin-top:8px;padding:12px;background:#1f2937;border-radius:10px;border:1px solid #374151;word-break:break-all;font-family:monospace;font-size:12px}
.hint{font-size:11px;color:#6b7280;margin-top:6px}
.rec{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:10px;margin:6px 0;font-size:12px}
.rec.revoked{border-color:#991b1b;background:#450a0a}
.rec .row{margin:1px 0} .rec b{font-size:12px}
.tag{display:inline-block;padding:1px 6px;border-radius:99px;font-size:10px;font-weight:700}
.tag.ok{background:#064e3b;color:#6ee7b7}.tag.exp{background:#7f1d1d;color:#fca5a5}.tag.rev{background:#374151;color:#9ca3af}.tag.pend{background:#1e3a5f;color:#93c5fd}
.expiry{color:#6ee7b7;font-weight:600}.expiry.expired{color:#fca5a5}.expiry.pending{color:#93c5fd}
.mach{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:10px;margin:6px 0;font-size:12px}
.mach .ttl{font-size:13px;font-weight:700}
.btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.chip{display:inline-flex;align-items:center;gap:4px;background:#7f1d1d;color:#fca5a5;padding:3px 8px;border-radius:99px;font-size:11px;font-weight:600;margin:3px 3px 0 0}
.chip button{background:none;border:0;color:#fca5a5;font-weight:800;padding:0 2px;margin:0;width:auto;font-size:12px}
.logout{position:fixed;top:8px;right:8px;background:#374151;border:0;color:#9ca3af;padding:4px 10px;border-radius:8px;font-size:11px}
.status{position:fixed;top:8px;left:8px;font-size:11px;padding:4px 10px;border-radius:8px;background:#064e3b;color:#6ee7b7;display:none}
.warn-banner{margin:0 0 12px;padding:10px 12px;border-radius:10px;background:#7f1d1d;color:#fecaca;font-size:12px;display:none}
.pkg-row{display:grid;grid-template-columns:1.2fr .6fr .6fr auto;gap:6px;align-items:center;margin:6px 0}
.pkg-row input,.pkg-row select{margin:0}
.filt button.on{background:#2563eb;color:#fff;border-color:#2563eb}
</style></head><body>
<form method="POST" action="${adminPath}/logout" style="position:fixed;top:8px;right:8px">
<button class="logout" type="submit">Logout</button>
</form>
<div id="status" class="status"></div>
<h1>SkyAdmin Pro</h1>
<div class="sub">Sky Creation Innovations</div>
<div id="keyBanner" class="warn-banner"></div>

<h2>Pricing Packages</h2>
<div class="hint">Shown on the desktop Pricing &amp; Activation page and iPhone generator.</div>
<div id="pkgEditor"></div>
<label>Over 1-year message</label>
<input id="overYear" placeholder="Over 1 Year — discuss on WhatsApp">
<div class="btns" style="margin-top:8px">
<button class="sm green" onclick="addPackageRow()">Add package</button>
<button class="sm gray" onclick="savePricing()">Save packages</button>
</div>

<h2>Generate License</h2>
<label>Machine ID</label>
<input id="mid" placeholder="72FA00DC6B64525F" autocomplete="off" autocapitalize="characters" spellcheck="false">
<label>Package</label>
<select id="days" onchange="document.getElementById('cWrap').style.display=this.value==='__custom__'?'block':'none'">
<option value="7" selected>Loading packages…</option>
</select>
<div id="cWrap" style="display:none"><label>Custom days</label><input id="cDays" type="number" min="1" max="36500"></div>
<button id="genBtn" onclick="generate()">Generate</button>

<div id="result" style="display:none">
<label>License Key</label>
<div id="license" class="out"></div>
<div class="btns"><button class="sm gray" onclick="copyEl('license')">Copy Key</button><button class="sm gray" onclick="copyEl('passcode')">Copy Passcode</button></div>
<label>Passcode</label>
<div id="passcode" class="out" style="font-size:18px;letter-spacing:3px;text-align:center"></div>
</div>

<h2>App Update</h2>
<div class="hint">Publishes <code>LATEST version url</code> on the control list — desktop apps show Settings → Download.</div>
<label>Version (e.g. 0.3.1)</label>
<input id="updVer" placeholder="0.3.1">
<label>Download URL</label>
<input id="updUrl" placeholder="https://your-cdn/SkyAdminPro.exe">
<div class="btns" style="margin-top:8px">
<button class="sm green" onclick="publishUpdate()">Publish update</button>
<button class="sm gray" onclick="loadUpdateInfo()">Reload</button>
</div>
<div id="updStatus" class="hint"></div>

<h2>Remote Control</h2>
<label>Ban machine</label>
<div style="display:flex;gap:6px">
<input id="banIn" placeholder="Machine ID" spellcheck="false" style="flex:1">
<button class="sm red" style="margin:0" onclick="addBan()">Ban</button>
</div>
<div id="banList"></div>

<h2>Machines <span id="machCnt" style="color:#6b7280;font-size:12px"></span></h2>
<div class="hint">Current license status per Machine ID (activated license preferred).</div>
<div class="btns filt" style="margin:8px 0">
<button type="button" class="sm gray" data-mf="all" onclick="setMachFilter('all')">All</button>
<button type="button" class="sm gray" data-mf="active" onclick="setMachFilter('active')">Active</button>
<button type="button" class="sm gray" data-mf="expiring" onclick="setMachFilter('expiring')">Expiring &lt;7d</button>
<button type="button" class="sm gray" data-mf="pending" onclick="setMachFilter('pending')">Pending</button>
<button type="button" class="sm gray" data-mf="expired" onclick="setMachFilter('expired')">Expired</button>
</div>
<input id="machSearch" placeholder="Search machine ID…" oninput="renderMachines()">
<div id="machines"></div>

<h2>Records <span id="cnt" style="color:#6b7280;font-size:12px"></span></h2>
<div class="btns filt" style="margin:8px 0">
<button type="button" class="sm gray" data-rf="all" onclick="setRecFilter('all')">All</button>
<button type="button" class="sm gray" data-rf="active" onclick="setRecFilter('active')">Active</button>
<button type="button" class="sm gray" data-rf="expiring" onclick="setRecFilter('expiring')">Expiring &lt;7d</button>
<button type="button" class="sm gray" data-rf="pending" onclick="setRecFilter('pending')">Pending</button>
<button type="button" class="sm gray" data-rf="expired" onclick="setRecFilter('expired')">Expired</button>
</div>
<input id="search" placeholder="Search..." oninput="renderRecords()">
<div id="records"></div>

<script>
var API_TOKEN=${JSON.stringify(apiToken)};
var _recs=[];
var _machines=[];
var _bans=[];
var _packages=[];
var _tickTimer=null;
var _machFilter='all';
var _recFilter='all';

function showStatus(m){
  var s=document.getElementById('status');s.textContent=m;s.style.display='block';
  setTimeout(function(){s.style.display='none';},2000);
}

function api(method,path,body){
  var init={method:method,headers:{'Content-Type':'application/json','Authorization':'Bearer '+API_TOKEN}};
  if(body)init.body=JSON.stringify(body);
  return fetch(path,init).then(function(r){
    if(!r.ok)return r.json().then(function(d){throw new Error(d.error||'API error '+r.status);});
    return r.json();
  }).then(function(d){if(!d.ok)throw new Error(d.error||'API error');return d;});
}

function loadRecords(){
  return api('GET','/api/records?limit=500').then(function(d){
    _recs=d.licenses||[];
    _machines=d.machines||[];
    renderMachines();
    renderRecords();
    startExpiryTicker();
  }).catch(function(e){console.error('loadRecords:',e);});
}
function loadBans(){
  return api('GET','/api/bans').then(function(d){_bans=d.bans||[];renderBans();}).catch(function(e){console.error('loadBans:',e);});
}

function fmtBaht(n){return Number(n||0).toLocaleString();}

function buildDaysSelect(){
  var sel=document.getElementById('days');
  sel.innerHTML='';
  for(var i=0;i<_packages.length;i++){
    var p=_packages[i];
    if(p.days===null) continue;
    var opt=document.createElement('option');
    opt.value=String(p.days);
    opt.textContent=p.label+' \u2014 '+fmtBaht(p.price_thb)+' Baht';
    if(p.days===7) opt.selected=true;
    sel.appendChild(opt);
  }
  var custom=document.createElement('option');
  custom.value='__custom__'; custom.textContent='Custom days...';
  sel.appendChild(custom);
  var never=document.createElement('option');
  never.value=''; never.textContent='Never (owner)';
  sel.appendChild(never);
}

function readPackageRows(){
  var rows=document.querySelectorAll('#pkgEditor .pkg-row');
  var out=[];
  for(var i=0;i<rows.length;i++){
    var row=rows[i];
    var label=(row.querySelector('.pkg-label')||{}).value||'';
    var days=parseInt((row.querySelector('.pkg-days')||{}).value,10);
    var price=parseInt((row.querySelector('.pkg-price')||{}).value,10);
    if(!label||!days||days<1) continue;
    out.push({label:label.trim(),days:days,price_thb:isNaN(price)?0:price});
  }
  return out;
}

function renderPackageEditor(){
  var box=document.getElementById('pkgEditor');
  box.innerHTML='';
  for(var i=0;i<_packages.length;i++){
    if(_packages[i].days===null) continue;
    addPackageRow(_packages[i]);
  }
}

function addPackageRow(pkg){
  pkg=pkg||{label:'',days:30,price_thb:0};
  var box=document.getElementById('pkgEditor');
  var row=document.createElement('div');
  row.className='pkg-row';
  row.innerHTML=
    '<input class="pkg-label" placeholder="Label" value="'+(pkg.label||'').replace(/"/g,'&quot;')+'">'+
    '<input class="pkg-days" type="number" min="1" max="36500" placeholder="Days" value="'+(pkg.days||'')+'">'+
    '<input class="pkg-price" type="number" min="0" placeholder="Baht" value="'+(pkg.price_thb||0)+'">'+
    '<button type="button" class="sm red" onclick="this.parentNode.remove()">Del</button>';
  box.appendChild(row);
}

function loadPricing(){
  return fetch('/api/pricing',{headers:{'Authorization':'Bearer '+API_TOKEN}}).then(function(r){return r.json();}).then(function(d){
    if(!d.ok) throw new Error(d.error||'pricing failed');
    _packages=d.packages||[];
    document.getElementById('overYear').value=d.over_year_text||'';
    renderPackageEditor();
    buildDaysSelect();
  }).catch(function(e){console.error('loadPricing:',e);});
}

function savePricing(){
  var packages=readPackageRows();
  if(!packages.length){alert('Add at least one package.');return;}
  api('POST','/api/pricing',{
    packages:packages,
    over_year_text:document.getElementById('overYear').value.trim()
  }).then(function(d){
    _packages=d.packages||packages;
    renderPackageEditor();
    buildDaysSelect();
    showStatus('Packages saved');
  }).catch(function(e){alert('Save failed: '+e.message);});
}

function priceForDays(days){
  for(var i=0;i<_packages.length;i++){
    if(_packages[i].days===days) return _packages[i].price_thb||0;
  }
  return 0;
}

function checkSigningKey(){
  fetch('/api/signing/public-key',{headers:{'Authorization':'Bearer '+API_TOKEN}}).then(function(r){return r.json();}).then(function(d){
    if(!d.ok) return;
    var el=document.getElementById('keyBanner');
    if(!d.matches_desktop){
      el.style.display='block';
      el.textContent='WARNING: Worker signing key does NOT match the desktop app. Activation codes will fail until LICENSE_ED25519_PRIVATE_KEY_B64 matches license_public.py (client key '+d.client_public_key_hex.slice(0,8)+'…).';
    }
  }).catch(function(){});
}

function parseExp(exp){
  if(!exp||exp==='never')return null;
  var t=String(exp);
  var d=new Date(t.endsWith('Z')?t:t+'Z');
  return isNaN(d.getTime())?null:d;
}

function timeLeftText(exp, used, revoked){
  if(revoked)return 'Revoked';
  var d=parseExp(exp);
  if(!d)return used?'Unlimited (activated)':'Unlimited (pending)';
  var ms=d.getTime()-Date.now();
  if(ms<=0){
    var ago=Math.abs(ms), days=Math.floor(ago/86400000), hrs=Math.floor((ago%86400000)/3600000);
    if(days>0)return 'Expired '+days+'d'+(hrs?' '+hrs+'h':'')+' ago';
    if(hrs>0)return 'Expired '+hrs+'h ago';
    return 'Expired';
  }
  var days=Math.floor(ms/86400000), hrs=Math.floor((ms%86400000)/3600000), mins=Math.floor((ms%3600000)/60000);
  var left='';
  if(days>0)left=days+'d'+(hrs?' '+hrs+'h':'');
  else if(hrs>0)left=hrs+'h'+(mins?' '+mins+'m':'');
  else left=Math.max(mins,1)+'m';
  return left+' left'+(used?'':' (not activated)');
}

function expiryClass(exp, revoked){
  if(revoked)return 'expired';
  var d=parseExp(exp);
  if(!d)return 'pending';
  return d.getTime()<=Date.now()?'expired':'';
}

function machStatusTag(st){
  var map={active:'ok',pending:'pend',expired:'exp',used_expired:'exp',revoked:'rev',unlimited:'ok',none:'rev'};
  var lbl={active:'ACTIVE',pending:'PENDING',expired:'EXPIRED',used_expired:'USED+EXPIRED',revoked:'REVOKED',unlimited:'UNLIMITED',none:'NONE'};
  return '<span class="tag '+(map[st]||'rev')+'">'+(lbl[st]||st.toUpperCase())+'</span>';
}

function setMachFilter(f){
  _machFilter=f;
  var btns=document.querySelectorAll('[data-mf]');
  for(var i=0;i<btns.length;i++){
    btns[i].className='sm gray'+(btns[i].getAttribute('data-mf')===f?' on':'');
  }
  renderMachines();
}
function setRecFilter(f){
  _recFilter=f;
  var btns=document.querySelectorAll('[data-rf]');
  for(var i=0;i<btns.length;i++){
    btns[i].className='sm gray'+(btns[i].getAttribute('data-rf')===f?' on':'');
  }
  renderRecords();
}

function matchesMachFilter(m){
  if(_machFilter==='all')return true;
  if(_machFilter==='active')return m.status==='active'||m.status==='unlimited';
  if(_machFilter==='expiring')return !!m.expiring_soon;
  if(_machFilter==='pending')return m.status==='pending';
  if(_machFilter==='expired')return m.is_expired||m.status==='expired'||m.status==='used_expired';
  return true;
}

function matchesRecFilter(r){
  if(_recFilter==='all')return true;
  var exp=r.expires_at||'never';
  var isRevoked=!!r.revoked;
  var isUsed=!!r.used;
  var isExpired=!!r.is_expired||isExpiredRecord(exp);
  var expSoon=!!r.expiring_soon||isExpiringSoon(exp,isRevoked);
  if(_recFilter==='active')return !isRevoked&&!isExpired&&isUsed;
  if(_recFilter==='expiring')return !isRevoked&&!isExpired&&expSoon;
  if(_recFilter==='pending')return !isRevoked&&!isUsed&&!isExpired;
  if(_recFilter==='expired')return !isRevoked&&isExpired;
  return true;
}

function isExpiringSoon(exp, revoked){
  if(revoked)return false;
  var ms=msRemaining(exp);
  return ms!==null&&ms>0&&ms<=7*86400000;
}

function msRemaining(exp){
  var d=parseExp(exp);
  if(!d)return null;
  return d.getTime()-Date.now();
}

function isExpiredRecord(exp){
  var ms=msRemaining(exp);
  return ms!==null&&ms<=0;
}

function startExpiryTicker(){
  if(_tickTimer)clearInterval(_tickTimer);
  _tickTimer=setInterval(function(){renderMachines();renderRecords();},60000);
}

function renderMachines(){
  var q=(document.getElementById('machSearch').value||'').toUpperCase();
  var box=document.getElementById('machines');box.innerHTML='';
  var shown=0;
  for(var i=0;i<_machines.length;i++){
    var m=_machines[i];
    var mid=m.machine_id||'';
    if(q&&mid.indexOf(q)<0)continue;
    if(!matchesMachFilter(m))continue;
    shown++;
    var exp=m.expires_at||'never';
    var left=timeLeftText(exp, m.status==='active'||m.status==='unlimited'||m.status==='used_expired', m.status==='revoked');
    var div=document.createElement('div');div.className='mach';
    var pkg=m.package_days==null?'Unlimited':m.package_days+'d';
    div.innerHTML=
      '<div class="row"><span class="ttl">'+mid+'</span> '+machStatusTag(m.status)+'</div>'+
      '<div class="row expiry '+expiryClass(exp,m.status==='revoked')+'">'+left+'</div>'+
      '<div class="row">Expires: '+(m.expires_label||'—')+' · Package: '+pkg+
      (m.issued_at?' · Issued: '+m.issued_at:'')+
      ' · '+m.license_count+' license(s)</div>';
    var b=document.createElement('div');b.className='btns';
    var mk=function(t,c,f){var x=document.createElement('button');x.className='sm '+c;x.textContent=t;x.onclick=f;return x;};
    b.appendChild(mk('Fill MID','gray',function(id){return function(){
      document.getElementById('mid').value=id;showStatus('Machine ID filled');};}(mid)));
    b.appendChild(mk('+7d','green',function(id){return function(){renew(id,7);};}(mid)));
    b.appendChild(mk('+30d','green',function(id){return function(){renew(id,30);};}(mid)));
    div.appendChild(b);box.appendChild(div);
  }
  document.getElementById('machCnt').textContent='('+shown+'/'+_machines.length+')';
  if(!box.children.length)box.innerHTML='<div class="hint">No machines match this filter.</div>';
}

function generate(){
  var mid=document.getElementById('mid').value.trim().toUpperCase();
  if(!mid||!/^[0-9A-F]{16}$/.test(mid)){alert('Enter 16-hex Machine ID');return;}
  var sel=document.getElementById('days').value;
  var days;
  if(sel==='__custom__'){days=parseInt(document.getElementById('cDays').value);if(!days||days<1){alert('Enter days');return;}}
  else if(sel===''){days=null;}
  else days=parseInt(sel);
  var btn=document.getElementById('genBtn');btn.disabled=true;btn.textContent='Signing...';
  api('POST','/api/generate',{mid:mid,days:days,price:priceForDays(days)}).then(function(d){
    document.getElementById('license').textContent=d.license_key;
    document.getElementById('passcode').textContent=d.passcode;
    document.getElementById('result').style.display='block';
    btn.disabled=false;btn.textContent='Generate';
    showStatus('Generated!');
    return loadRecords();
  }).catch(function(e){alert('Failed: '+e.message);btn.disabled=false;btn.textContent='Generate';});
}

function renderRecords(){
  var q=(document.getElementById('search').value||'').toUpperCase();
  var box=document.getElementById('records');box.innerHTML='';
  var shown=0;
  for(var i=0;i<_recs.length;i++){
    var r=_recs[i];
    var mid=r.machine_id||'';
    if(q&&mid.indexOf(q)<0)continue;
    if(!matchesRecFilter(r))continue;
    shown++;
    var nonce=r.nonce||'';
    var key=r.license_key||'';
    var pass=r.passcode||'';
    var pkg=r.package_days;
    var exp=r.expires_at||'never';
    var price=r.price_thb||0;
    var ts=r.issued_at||'';
    var isRevoked=r.revoked;
    var isUsed=r.used;
    var isExpired=r.is_expired||(exp!=='never'&&parseExp(exp)&&parseExp(exp).getTime()<=Date.now());
    var tag=isRevoked?'<span class="tag rev">REVOKED</span>':isExpired?'<span class="tag exp">EXPIRED</span>':isUsed?'<span class="tag ok">ACTIVE</span>':'<span class="tag pend">PENDING</span>';
    var left=r.time_left||timeLeftText(exp,isUsed,isRevoked);
    var expLabel=r.expires_label||(exp==='never'?'Never expires':exp);
    var d=document.createElement('div');d.className='rec'+(isRevoked?' revoked':'');
    var pkgStr=(pkg===null||pkg===undefined)?'Unlimited':pkg+'d';
    d.innerHTML='<div class="row"><b>'+mid+'</b> '+tag+'</div>'+
      '<div class="row expiry '+expiryClass(exp,isRevoked)+'">'+left+'</div>'+
      '<div class="row">Expires: '+expLabel+' · '+pkgStr+(price?' · '+price+'\u0e3f':'')+' · Issued: '+ts+'</div>';
    var b=document.createElement('div');b.className='btns';
    var mk=function(t,c,f){var x=document.createElement('button');x.className='sm '+c;x.textContent=t;x.onclick=f;return x;};
    b.appendChild(mk('Copy key','gray',function(k){return function(){navigator.clipboard.writeText(k);showStatus('Copied');};}(key)));
    b.appendChild(mk('Copy PC','gray',function(p){return function(){navigator.clipboard.writeText(p);showStatus('Copied');};}(pass)));
    b.appendChild(mk('+7d','green',function(m){return function(){renew(m,7);};}(mid)));
    b.appendChild(mk('+30d','green',function(m){return function(){renew(m,30);};}(mid)));
    if(!isRevoked)b.appendChild(mk('Revoke','red',function(n){return function(){doRevoke(n);};}(nonce)));
    if(isRevoked)b.appendChild(mk('Unrevoke','gray',function(n){return function(){doUnrevoke(n);};}(nonce)));
    d.appendChild(b);box.appendChild(d);
  }
  document.getElementById('cnt').textContent='('+shown+'/'+_recs.length+')';
  if(!box.children.length)box.innerHTML='<div class="hint">No records match this filter.</div>';
}

function renew(mid,days){
  var price=priceForDays(days);
  api('POST','/api/generate',{mid:mid,days:days,price:price}).then(function(d){
    navigator.clipboard.writeText(d.license_key);
    showStatus(days+'d generated & copied');
    return loadRecords();
  }).catch(function(e){alert(e.message);});
}

function doRevoke(nonce){
  if(!confirm('Revoke this license?'))return;
  api('POST','/api/revoke',{nonce:nonce}).then(function(){
    showStatus('Revoked');
    return loadRecords();
  }).catch(function(e){alert(e.message);});
}
function doUnrevoke(nonce){
  api('POST','/api/unrevoke',{nonce:nonce}).then(function(){
    showStatus('Un-revoked');
    return loadRecords();
  }).catch(function(e){alert(e.message);});
}

function loadUpdateInfo(){
  return fetch('/api/update',{headers:{'Authorization':'Bearer '+API_TOKEN}}).then(function(r){return r.json();}).then(function(d){
    if(!d.ok)return;
    if(d.version)document.getElementById('updVer').value=d.version;
    if(d.url)document.getElementById('updUrl').value=d.url;
    var st=document.getElementById('updStatus');
    st.textContent=d.version?'Current: v'+d.version+(d.url?' → '+d.url:''):'No update published yet.';
  }).catch(function(){});
}

function publishUpdate(){
  var version=(document.getElementById('updVer').value||'').trim();
  var url=(document.getElementById('updUrl').value||'').trim();
  if(!version){alert('Enter a version number.');return;}
  api('POST','/api/update',{version:version,url:url}).then(function(d){
    showStatus('Update published');
    document.getElementById('updStatus').textContent='Published v'+version+(url?' → '+url:'');
  }).catch(function(e){alert('Publish failed: '+e.message);});
}

function addBan(){
  var mid=document.getElementById('banIn').value.trim().toUpperCase();
  if(!/^[0-9A-F]{16}$/.test(mid)){alert('16 hex chars');return;}
  api('POST','/api/ban',{mid:mid}).then(function(){
    document.getElementById('banIn').value='';
    showStatus('Banned');
    return loadBans();
  }).catch(function(e){alert(e.message);});
}

function renderBans(){
  var box=document.getElementById('banList');box.innerHTML='';
  if(!_bans.length){box.innerHTML='<div class="hint">No bans.</div>';return;}
  for(var i=0;i<_bans.length;i++){
    var b=_bans[i];var m=b.machine_id;
    (function(m){
      var c=document.createElement('span');c.className='chip';c.textContent=m+' ';
      var x=document.createElement('button');x.textContent='\u2715';x.onclick=function(){
        api('POST','/api/unban',{mid:m}).then(function(){
          showStatus('Unbanned');
          loadBans();
        }).catch(function(e){alert(e.message);});
      };c.appendChild(x);box.appendChild(c);
    })(m);
  }
}

function copyEl(id){navigator.clipboard.writeText(document.getElementById(id).textContent);showStatus('Copied');}

loadPricing().then(function(){
  setMachFilter('all');setRecFilter('all');
  loadUpdateInfo();
  loadRecords();loadBans();checkSigningKey();
});
</script></body></html>`;

export async function adminHandler(c: Context<{ Bindings: Env }>): Promise<Response> {
  const url = new URL(c.req.url);
  const path = url.pathname;
  const adminPath = "/" + c.env.ADMIN_PATH;
  const ip = c.req.header("cf-connecting-ip") || "unknown";

  // Login POST — form-encoded password
  if (path.endsWith("/login") && c.req.method === "POST") {
    // Check if IP is blocked
    if (await isIpBlocked(c, ip)) {
      return c.html(loginPage(adminPath, "Too many attempts. Try again later."), 429);
    }

    try {
      const body = await c.req.parseBody();
      const pw = typeof body.password === "string" ? body.password : "";

      // Validate CSRF token
      const csrfToken = typeof body.csrf_token === "string" ? body.csrf_token : "";
      if (!csrfToken || !(await validateCsrfToken(csrfToken, c.env.ADMIN_PASS, c.env.ADMIN_PATH))) {
        return c.html(loginPage(adminPath, "Invalid form. Please try again."), 403);
      }

      if (pw === c.env.ADMIN_PASS) {
        // Clear failed attempts on success
        await c.env.DB.prepare("DELETE FROM login_attempts WHERE ip = ?").bind(ip).run();

        const cookieName = sessionKey(adminSessionSalt(c.env));
        const token = await hmacSign(c.env.ADMIN_PASS, c.env.ADMIN_PATH + ":session");
        return new Response(null, {
          status: 303,
          headers: {
            Location: adminPath + "/",
            "Set-Cookie": `${cookieName}=${token}; Max-Age=${SESSION_TTL}; Path=/; HttpOnly; Secure; SameSite=Lax`,
          },
        });
      }

      // Record failed attempt
      await recordLoginAttempt(c, ip);
    } catch {}
    return c.html(loginPage(adminPath, "Wrong password"), 401);
  }

  // Logout POST
  if (path.endsWith("/logout") && c.req.method === "POST") {
    const cookieName = sessionKey(adminSessionSalt(c.env));
    return new Response(null, {
      status: 303,
      headers: {
        Location: adminPath + "/",
        "Set-Cookie": `${cookieName}=; Max-Age=0; Path=/`,
      },
    });
  }

  // Check session
  if (!(await isValidSession(c))) {
    // Generate CSRF token for login page
    const csrfToken = await generateCsrfToken(c.env.ADMIN_PASS, c.env.ADMIN_PATH);
    const page = loginPage(adminPath).replace(
      '<input type="hidden" name="csrf_token" value="">',
      `<input type="hidden" name="csrf_token" value="${csrfToken}">`
    );
    return c.html(page);
  }

  return c.html(ADMIN_HTML_BUILDER(adminPath, c.env.API_TOKEN));
}
