/** Admin page — hidden generator UI served at a secret path. */

import { Context } from "hono";
import { getCookie, setCookie } from "hono/cookie";
import { Env } from "../db";
import { hmacSign } from "../signing";

const SESSION_TTL = 86400 * 7; // 7 days
const CSRF_TTL = 3600; // 1 hour
const MAX_LOGIN_ATTEMPTS = 5;
const LOGIN_BLOCK_MINUTES = 15;

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
  const cookieName = sessionKey(c.env.LICENSE_SECRET);
  const token = getCookie(c, cookieName);
  if (!token) return false;
  const expected = await hmacSign(c.env.ADMIN_PASS, c.env.ADMIN_PATH + ":session");
  return token === expected;
}

async function isIpBlocked(c: Context<{ Bindings: Env }>, ip: string): Promise<boolean> {
  const cutoff = new Date(Date.now() - LOGIN_BLOCK_MINUTES * 60 * 1000).toISOString();
  const { results } = await c.env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM login_attempts WHERE ip = ? AND attempted_at > ?"
  ).bind(ip, cutoff).first<{ cnt: number }>();
  return (results?.cnt ?? 0) >= MAX_LOGIN_ATTEMPTS;
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

const ADMIN_HTML_BUILDER = (adminPath: string) => `<!DOCTYPE html>
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
.tag.ok{background:#064e3b;color:#6ee7b7}.tag.exp{background:#7f1d1d;color:#fca5a5}.tag.rev{background:#374151;color:#9ca3af}
.btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.chip{display:inline-flex;align-items:center;gap:4px;background:#7f1d1d;color:#fca5a5;padding:3px 8px;border-radius:99px;font-size:11px;font-weight:600;margin:3px 3px 0 0}
.chip button{background:none;border:0;color:#fca5a5;font-weight:800;padding:0 2px;margin:0;width:auto;font-size:12px}
.logout{position:fixed;top:8px;right:8px;background:#374151;border:0;color:#9ca3af;padding:4px 10px;border-radius:8px;font-size:11px}
.status{position:fixed;top:8px;left:8px;font-size:11px;padding:4px 10px;border-radius:8px;background:#064e3b;color:#6ee7b7;display:none}
</style></head><body>
<form method="POST" action="${adminPath}/logout" style="position:fixed;top:8px;right:8px">
<button class="logout" type="submit">Logout</button>
</form>
<div id="status" class="status"></div>
<h1>SkyAdmin Pro</h1>
<div class="sub">Sky Creation Innovations</div>

<h2>Generate License</h2>
<label>Machine ID</label>
<input id="mid" placeholder="72FA00DC6B64525F" autocomplete="off" autocapitalize="characters" spellcheck="false">
<label>Package</label>
<select id="days" onchange="document.getElementById('cWrap').style.display=this.value==='__custom__'?'block':'none'">
<option value="1">1 Day \u2014 50 Baht</option>
<option value="7" selected>7 Days \u2014 500 Baht</option>
<option value="30">30 Days \u2014 800 Baht</option>
<option value="365">1 Year \u2014 9,000 Baht</option>
<option value="__custom__">Custom days...</option>
<option value="">Never (owner)</option>
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

<h2>Remote Control</h2>
<label>Ban machine</label>
<div style="display:flex;gap:6px">
<input id="banIn" placeholder="Machine ID" spellcheck="false" style="flex:1">
<button class="sm red" style="margin:0" onclick="addBan()">Ban</button>
</div>
<div id="banList"></div>

<h2>Records <span id="cnt" style="color:#6b7280;font-size:12px"></span></h2>
<input id="search" placeholder="Search..." oninput="renderRecords()">
<div id="records"></div>

<script>
var _recs=[];
var _bans=[];

function showStatus(m){
  var s=document.getElementById('status');s.textContent=m;s.style.display='block';
  setTimeout(function(){s.style.display='none';},2000);
}

function api(method,path,body){
  var init={method:method,headers:{'Content-Type':'application/json'}};
  if(body)init.body=JSON.stringify(body);
  return fetch(path,init).then(function(r){
    if(!r.ok)return r.json().then(function(d){throw new Error(d.error||'API error '+r.status);});
    return r.json();
  }).then(function(d){if(!d.ok)throw new Error(d.error||'API error');return d;});
}

function loadRecords(){
  return api('GET','/api/records').then(function(d){_recs=d.licenses||[];renderRecords();}).catch(function(e){console.error('loadRecords:',e);});
}
function loadBans(){
  return api('GET','/api/bans').then(function(d){_bans=d.bans||[];renderBans();}).catch(function(e){console.error('loadBans:',e);});
}

function generate(){
  var mid=document.getElementById('mid').value.trim().toUpperCase();
  if(!mid||!/^[0-9A-F]{16}/.test(mid)){alert('Enter 16-hex Machine ID');return;}
  var sel=document.getElementById('days').value;
  var days;
  if(sel==='__custom__'){days=parseInt(document.getElementById('cDays').value);if(!days||days<1){alert('Enter days');return;}}
  else if(sel===''){days=null;}
  else days=parseInt(sel);
  var prices={1:50,7:500,30:800,365:9000};
  var btn=document.getElementById('genBtn');btn.disabled=true;btn.textContent='Signing...';
  api('POST','/api/generate',{mid:mid,days:days,price:prices[days]||0}).then(function(d){
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
  document.getElementById('cnt').textContent='('+_recs.length+')';
  for(var i=0;i<_recs.length;i++){
    var r=_recs[i];
    var mid=r.machine_id||'';
    if(q&&mid.indexOf(q)<0)continue;
    var nonce=r.nonce||'';
    var key=r.license_key||'';
    var pass=r.passcode||'';
    var pkg=r.package_days;
    var exp=r.expires_at||'never';
    var price=r.price_thb||0;
    var ts=r.issued_at||'';
    var isRevoked=r.revoked;
    var isUsed=r.used;
    var isExpired=exp!=='never'&&new Date(exp)<new Date();
    var tag=isRevoked?'<span class="tag rev">REVOKED</span>':isUsed?'<span class="tag rev">USED</span>':isExpired?'<span class="tag exp">EXPIRED</span>':'<span class="tag ok">ACTIVE</span>';
    var d=document.createElement('div');d.className='rec'+(isRevoked?' revoked':'');
    var pkgStr=(pkg===null||pkg===undefined)?'Unlimited':pkg+'d';
    d.innerHTML='<div class="row"><b>'+mid+'</b> '+tag+'</div><div class="row">'+pkgStr+(price?' \u00b7 '+price+'\u0e3f':'')+' \u00b7 '+ts+'</div>';
    var b=document.createElement('div');b.className='btns';
    var mk=function(t,c,f){var x=document.createElement('button');x.className='sm '+c;x.textContent=t;x.onclick=f;return x;};
    b.appendChild(mk('Copy key','gray',function(k){return function(){navigator.clipboard.writeText(k);showStatus('Copied');};}(key)));
    b.appendChild(mk('Copy PC','gray',function(p){return function(){navigator.clipboard.writeText(p);showStatus('Copied');};}(pass)));
    b.appendChild(mk('+7d','green',function(m){return function(){renew(m,7,500);};}(mid)));
    b.appendChild(mk('+30d','green',function(m){return function(){renew(m,30,800);};}(mid)));
    if(!isRevoked)b.appendChild(mk('Revoke','red',function(n){return function(){doRevoke(n);};}(nonce)));
    if(isRevoked)b.appendChild(mk('Unrevoke','gray',function(n){return function(){doUnrevoke(n);};}(nonce)));
    d.appendChild(b);box.appendChild(d);
  }
  if(!box.children.length)box.innerHTML='<div class="hint">No records.</div>';
}

function renew(mid,days,price){
  var prices={1:50,7:500,30:800,365:9000};
  api('POST','/api/generate',{mid:mid,days:days,price:prices[days]||0}).then(function(d){
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

function addBan(){
  var mid=document.getElementById('banIn').value.trim().toUpperCase();
  if(!/^[0-9A-F]{16}/.test(mid)){alert('16 hex chars');return;}
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

loadRecords();loadBans();
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

        const cookieName = sessionKey(c.env.LICENSE_SECRET);
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
    const cookieName = sessionKey(c.env.LICENSE_SECRET);
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

  return c.html(ADMIN_HTML_BUILDER(adminPath));
}
