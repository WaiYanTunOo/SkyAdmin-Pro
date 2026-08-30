/** P4.1 — read-only mobile/PWA viewer (office_contacts + notebook_entries). */

import { Context } from "hono";

const VIEWER_TABLES = "clients,tasks,office_contacts,notebook_entries";

export function viewerManifestHandler(_c: Context) {
  const body = JSON.stringify({
    name: "SkyAdmin Viewer",
    short_name: "SkyAdmin",
    description: "Read-only clients, tasks, contacts, and notebook",
    start_url: "/viewer",
    display: "standalone",
    background_color: "#111827",
    theme_color: "#2563eb",
    icons: [
      {
        src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'%3E%3Crect fill='%232563eb' width='192' height='192' rx='32'/%3E%3Ctext x='96' y='118' text-anchor='middle' fill='white' font-size='72' font-family='system-ui' font-weight='700'%3ES%3C/text%3E%3C/svg%3E",
        sizes: "192x192",
        type: "image/svg+xml",
      },
    ],
  });
  return new Response(body, {
    headers: {
      "Content-Type": "application/manifest+json",
      "Cache-Control": "public, max-age=3600",
    },
  });
}

export function viewerServiceWorkerHandler(_c: Context) {
  const js = `const CACHE="skyadmin-viewer-v2";
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(["/viewer","/viewer/manifest.webmanifest"])));self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(self.clients.claim())});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);if(u.pathname.startsWith("/viewer")){e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)))}});`;
  return new Response(js, {
    headers: {
      "Content-Type": "application/javascript",
      "Cache-Control": "public, max-age=3600",
    },
  });
}

export function viewerHandler(_c: Context) {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2563eb">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="SkyAdmin">
<link rel="manifest" href="/viewer/manifest.webmanifest">
<title>SkyAdmin Viewer</title>
<style>
:root{color-scheme:dark;--bg:#0f172a;--card:#1e293b;--muted:#94a3b8;--text:#f8fafc;--accent:#3b82f6;--border:#334155}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{position:sticky;top:0;z-index:10;background:#111827ee;backdrop-filter:blur(8px);border-bottom:1px solid var(--border);padding:12px 16px;padding-top:max(12px,env(safe-area-inset-top))}
header h1{margin:0;font-size:18px;font-weight:700}
header p{margin:4px 0 0;font-size:12px;color:var(--muted)}
.toolbar{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
input,select,button,textarea{font:inherit}
input,select{flex:1;min-width:0;padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:#0b1220;color:var(--text)}
button{padding:10px 14px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer}
button.secondary{background:#334155}
button:disabled{opacity:.5;cursor:not-allowed}
.tabs{display:flex;gap:4px;padding:8px 16px;border-bottom:1px solid var(--border);background:#111827;overflow-x:auto;-webkit-overflow-scrolling:touch}
.tab{flex:0 0 auto;min-width:72px;padding:10px 12px;border:0;border-radius:10px;background:transparent;color:var(--muted);font-weight:600;cursor:pointer;font-size:13px}
.tab.active{background:var(--card);color:var(--text)}
main{padding:12px 16px 24px;padding-bottom:max(24px,env(safe-area-inset-bottom))}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;margin-bottom:10px}
.card h3{margin:0 0 6px;font-size:16px}
.meta{font-size:12px;color:var(--muted);line-height:1.5}
.body{margin-top:8px;font-size:14px;line-height:1.55;white-space:pre-wrap}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#1d4ed833;color:#93c5fd;font-size:11px;font-weight:600;margin-right:6px}
.pin{color:#fbbf24}
.empty{text-align:center;color:var(--muted);padding:40px 16px}
.status{font-size:12px;color:var(--muted);margin-top:8px}
.error{color:#fca5a5}
#activate{padding:24px 16px;max-width:480px;margin:0 auto}
#activate textarea{width:100%;min-height:120px;padding:12px;border:1px solid var(--border);border-radius:12px;background:#0b1220;color:var(--text);resize:vertical}
#activate label{display:block;font-size:13px;color:var(--muted);margin:12px 0 6px}
.hidden{display:none!important}
</style>
</head>
<body>
<div id="activate">
  <header style="position:static;border:0;background:transparent;padding:0 0 16px">
    <h1>SkyAdmin Viewer</h1>
    <p>Read-only clients, tasks, contacts, and notebook. Paste your activation code from the desktop app.</p>
  </header>
  <label for="code">License key or passcode</label>
  <textarea id="code" placeholder="Paste SKYPASS1:… or license key"></textarea>
  <div class="toolbar" style="margin-top:12px">
    <button id="btnActivate" type="button">Activate</button>
  </div>
  <p id="activateStatus" class="status"></p>
</div>

<div id="app" class="hidden">
  <header>
    <h1>SkyAdmin Viewer</h1>
    <p id="machineLabel">Read-only · synced from desktop</p>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Search…" autocomplete="off">
      <button id="btnRefresh" type="button">Refresh</button>
      <button id="btnLogout" type="button" class="secondary">Sign out</button>
    </div>
    <p id="syncStatus" class="status"></p>
  </header>
  <div class="tabs">
    <button class="tab active" data-tab="clients" type="button">Clients</button>
    <button class="tab" data-tab="tasks" type="button">Tasks</button>
    <button class="tab" data-tab="contacts" type="button">Contacts</button>
    <button class="tab" data-tab="notebook" type="button">Notebook</button>
  </div>
  <main>
    <div id="panel-clients"></div>
    <div id="panel-tasks" class="hidden"></div>
    <div id="panel-contacts" class="hidden"></div>
    <div id="panel-notebook" class="hidden"></div>
  </main>
</div>

<script>
const STORAGE_KEY="skyadmin_viewer_creds";
const VIEWER_TABLES=${JSON.stringify(VIEWER_TABLES)};
const NOTE_TYPES={daily_report:"Daily report",weekly_report:"Weekly report",customer_instruction:"Customer instruction",senior_note:"Senior note",general:"General"};
const TASK_STATUS={pending:"Pending",completed:"Done"};

let state={clients:[],tasks:[],contacts:[],notes:[],tab:"clients"};

function $(id){return document.getElementById(id)}
function loadCreds(){try{return JSON.parse(localStorage.getItem(STORAGE_KEY)||"null")}catch{return null}}
function saveCreds(c){localStorage.setItem(STORAGE_KEY,JSON.stringify(c))}
function clearCreds(){localStorage.removeItem(STORAGE_KEY)}

function showActivate(msg,isError){
  $("activate").classList.remove("hidden");
  $("app").classList.add("hidden");
  const el=$("activateStatus");
  el.textContent=msg||"";
  el.className="status"+(isError?" error":"");
}

function showApp(){
  $("activate").classList.add("hidden");
  $("app").classList.remove("hidden");
}

function esc(s){
  return String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function activeRows(changes,table){
  const map=new Map();
  for(const ch of changes){
    if(ch.table!==table)continue;
    if(ch.deleted_at)continue;
    const row=ch.row||{};
    map.set(ch.global_id,{...row,global_id:ch.global_id,updated_at:ch.updated_at});
  }
  return [...map.values()];
}

async function register(code){
  const res=await fetch("/api/sync/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code:code.trim()})});
  const data=await res.json();
  if(!res.ok||!data.ok)throw new Error(data.error||("HTTP "+res.status));
  return {machine_id:data.machine_id,sync_token:data.sync_token};
}

async function pull(creds){
  const url="/api/sync/pull?tables="+encodeURIComponent(VIEWER_TABLES);
  const res=await fetch(url,{headers:{Authorization:"Bearer "+creds.sync_token,"X-Machine-Id":creds.machine_id}});
  const data=await res.json();
  if(!res.ok||!data.ok)throw new Error(data.error||("HTTP "+res.status));
  return data;
}

async function syncNow(){
  const creds=loadCreds();
  if(!creds)return showActivate();
  $("syncStatus").textContent="Syncing…";
  try{
    const data=await pull(creds);
    state.clients=activeRows(data.changes||[],"clients").sort((a,b)=>(a.name||"").localeCompare(b.name||""));
    state.tasks=activeRows(data.changes||[],"tasks").sort((a,b)=>{
      const ad=a.due_date||"9999",bd=b.due_date||"9999";
      if(ad!==bd)return ad.localeCompare(bd);
      return (a.title||"").localeCompare(b.title||"");
    });
    state.contacts=activeRows(data.changes||[],"office_contacts").sort((a,b)=>(a.name||"").localeCompare(b.name||""));
    state.notes=activeRows(data.changes||[],"notebook_entries").sort((a,b)=>(b.entry_date||"").localeCompare(a.entry_date||""));
    $("machineLabel").textContent="Machine "+creds.machine_id+" · read-only";
    $("syncStatus").textContent="Updated "+(data.server_time||new Date().toISOString());
    render();
  }catch(err){
    $("syncStatus").textContent="";
    $("syncStatus").className="status error";
    $("syncStatus").textContent=String(err.message||err);
  }
}

function matchSearch(row,fields){
  const q=($("search").value||"").trim().toLowerCase();
  if(!q)return true;
  return fields.some(f=>String(row[f]||"").toLowerCase().includes(q));
}

function clientName(gid){
  if(!gid)return "";
  const c=state.clients.find(r=>r.global_id===gid);
  return c?(c.name||c.company_name||"Client"):"";
}

function renderClients(){
  const el=$("panel-clients");
  const rows=state.clients.filter(r=>matchSearch(r,["name","company_name","contact_name","email","status","service_type","contact_number","notes"]));
  if(!rows.length){el.innerHTML='<div class="empty">No clients match.</div>';return}
  el.innerHTML=rows.map(r=>'<article class="card"><h3>'+esc(r.name)+'</h3><div class="meta"><span class="badge">'+esc(r.status||"active")+'</span>'+
    (r.service_type?'<span class="badge">'+esc(r.service_type)+'</span>':"")+
    (r.payment_status?'<span class="badge">'+esc(r.payment_status)+'</span>':"")+'</div>'+
    [r.company_name,r.contact_name,r.contact_number&&("📞 "+r.contact_number),r.email&&("✉ "+r.email)].filter(Boolean).map(x=>'<div class="meta">'+esc(x)+'</div>').join("")+
    (r.notes?'<div class="body">'+esc(r.notes)+'</div>':"")+'</article>').join("");
}

function renderTasks(){
  const el=$("panel-tasks");
  const rows=state.tasks.filter(r=>matchSearch(r,["title","description","category","status","due_date"]));
  if(!rows.length){el.innerHTML='<div class="empty">No tasks match.</div>';return}
  el.innerHTML=rows.map(r=>{
    const client=clientName(r.client_global_id);
    const done=r.status==="completed";
    return '<article class="card"><h3>'+(done?"✓ ":"")+esc(r.title)+'</h3><div class="meta"><span class="badge">'+esc(TASK_STATUS[r.status]||r.status||"Task")+'</span>'+
      (r.category?'<span class="badge">'+esc(r.category)+'</span>':"")+
      (client?'<span class="badge">'+esc(client)+'</span>':"")+'</div>'+
      (r.due_date?'<div class="meta">Due '+esc(r.due_date)+'</div>':"")+
      (r.description?'<div class="body">'+esc(r.description)+'</div>':"")+'</article>';
  }).join("");
}

function renderContacts(){
  const el=$("panel-contacts");
  const rows=state.contacts.filter(r=>matchSearch(r,["name","organization","department","phone","email","category","notes"]));
  if(!rows.length){el.innerHTML='<div class="empty">No contacts match.</div>';return}
  el.innerHTML=rows.map(r=>'<article class="card"><h3>'+esc(r.name)+(r.is_favorite?'<span class="pin"> ★</span>':"")+'</h3><div class="meta"><span class="badge">'+esc(r.category||"Office")+'</span>'+
    [r.role_title,r.organization,r.department].filter(Boolean).map(esc).join(" · ")+'</div>'+
    [r.phone&&("📞 "+r.phone),r.email&&("✉ "+r.email),r.line_id&&("LINE "+r.line_id)].filter(Boolean).map(x=>'<div class="meta">'+esc(x)+'</div>').join("")+
    (r.notes?'<div class="body">'+esc(r.notes)+'</div>':"")+'</article>').join("");
}

function renderNotes(){
  const el=$("panel-notebook");
  const rows=state.notes.filter(r=>matchSearch(r,["title","body","author","entry_type"]));
  if(!rows.length){el.innerHTML='<div class="empty">No notebook entries match.</div>';return}
  el.innerHTML=rows.map(r=>'<article class="card"><h3>'+(r.is_pinned?'<span class="pin">📌 </span>':"")+esc(r.title)+'</h3><div class="meta"><span class="badge">'+esc(NOTE_TYPES[r.entry_type]||r.entry_type||"Note")+'</span>'+
    esc(r.entry_date||"")+(r.author?" · "+esc(r.author):"")+(r.follow_up_date?" · Follow-up "+esc(r.follow_up_date):"")+'</div>'+
    (r.body?'<div class="body">'+esc(r.body)+'</div>':"")+'</article>').join("");
}

function render(){
  const panels={clients:"panel-clients",tasks:"panel-tasks",contacts:"panel-contacts",notebook:"panel-notebook"};
  Object.values(panels).forEach(id=>$(id).classList.add("hidden"));
  $(panels[state.tab]).classList.remove("hidden");
  if(state.tab==="clients")renderClients();
  else if(state.tab==="tasks")renderTasks();
  else if(state.tab==="contacts")renderContacts();
  else renderNotes();
}

document.querySelectorAll(".tab").forEach(btn=>{
  btn.addEventListener("click",()=>{
    document.querySelectorAll(".tab").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active");
    state.tab=btn.dataset.tab;
    render();
  });
});

$("search").addEventListener("input",render);
$("btnRefresh").addEventListener("click",syncNow);
$("btnLogout").addEventListener("click",()=>{clearCreds();showActivate("Signed out.")});
$("btnActivate").addEventListener("click",async()=>{
  const code=$("code").value.trim();
  if(!code)return showActivate("Paste your activation code.",true);
  $("btnActivate").disabled=true;
  showActivate("Activating…");
  try{
    const creds=await register(code);
    saveCreds(creds);
    showApp();
    await syncNow();
  }catch(err){
    showActivate(String(err.message||err),true);
  }finally{$("btnActivate").disabled=false}
});

if("serviceWorker" in navigator){navigator.serviceWorker.register("/viewer/sw.js").catch(()=>{})}

if(loadCreds()){showApp();syncNow()}else{showActivate()}
</script>
</body>
</html>`;
  return new Response(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
}
