export const getJsPart3 = () => `
function renderContacts(){
  const el=$("panel-contacts");
  const q=($("search").value||"").trim();
  const rows=state.contacts.filter(r=>matchSearch(r,["name","organization","department","phone","email","category","notes"]));
  if(!rows.length){
    el.innerHTML=emptyHtml(q?"No contacts match":"No contacts yet",q?"Try another search.":"Sync from desktop to populate contacts.");
    return;
  }
  el.innerHTML=rows.map(r=>'<article class="card"><h3>'+esc(r.name)+(r.is_favorite?'<span class="pin"> ★</span>':"")+'</h3><div class="meta"><span class="badge">'+esc(r.category||"Office")+'</span>'+
    [r.role_title,r.organization,r.department].filter(Boolean).map(esc).join(" · ")+'</div>'+
    [r.phone&&("📞 "+r.phone),r.email&&("✉ "+r.email),r.line_id&&("LINE "+r.line_id)].filter(Boolean).map(x=>'<div class="meta">'+esc(x)+'</div>').join("")+
    (r.notes?'<div class="body">'+esc(r.notes)+'</div>':"")+'</article>').join("");
}

function renderNotes(){
  const el=$("panel-notebook");
  const q=($("search").value||"").trim();
  const rows=state.notes.filter(r=>matchSearch(r,["title","body","author","entry_type"]));
  if(!rows.length){
    el.innerHTML=emptyHtml(q?"No notebook entries match":"No notebook entries yet",q?"Try another search.":"Sync from desktop to populate notebook.");
    return;
  }
  el.innerHTML=rows.map(r=>'<article class="card"><h3>'+(r.is_pinned?'<span class="pin">📌 </span>':"")+esc(r.title)+'</h3><div class="meta"><span class="badge">'+esc(NOTE_TYPES[r.entry_type]||r.entry_type||"Note")+'</span>'+
    esc(r.entry_date||"")+(r.author?" · "+esc(r.author):"")+(r.follow_up_date?" · Follow-up "+esc(r.follow_up_date):"")+'</div>'+
    (r.body?'<div class="body">'+esc(r.body)+'</div>':"")+'</article>').join("");
}

function render(){
  const panels={groups:"panel-groups",clients:"panel-clients",tasks:"panel-tasks",contacts:"panel-contacts",notebook:"panel-notebook",passwords:"panel-passwords"};
  Object.values(panels).forEach(id=>$(id).classList.add("hidden"));
  $(panels[state.tab]||"panel-groups").classList.remove("hidden");
  if(state.tab==="groups")renderGroups();
  else if(state.tab==="clients")renderClients();
  else if(state.tab==="tasks")renderTasks();
  else if(state.tab==="contacts")renderContacts();
  else if(state.tab==="passwords")renderPasswords();
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

wireVaultUi();

if("serviceWorker" in navigator){navigator.serviceWorker.register("/viewer/sw.js").catch(()=>{})}

if(loadCreds()){
  showApp();
  const last=loadLastSync();
  if(last)$("syncStatus").textContent=formatSyncLabel(last);
  syncNow();
}else{showActivate()}
`;
