export const getJsPart1 = () => `
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

function formatSyncLabel(iso){
  if(!iso)return "Never synced";
  try{
    const d=new Date(iso);
    if(Number.isNaN(d.getTime()))return "Last synced "+iso;
    return "Last synced "+d.toLocaleString();
  }catch{return "Last synced "+iso}
}

async function syncNow(){
  const creds=loadCreds();
  if(!creds)return showActivate();
  $("syncStatus").className="status";
  $("syncStatus").textContent="Syncing…";
  try{
    const data=await pull(creds);
    const changes=data.changes||[];
    state.groups=activeRows(changes,"client_groups").sort((a,b)=>(a.name||"").localeCompare(b.name||""));
    state.clients=activeRows(changes,"clients").sort((a,b)=>(a.name||"").localeCompare(b.name||""));
    state.tasks=activeRows(changes,"tasks").sort((a,b)=>{
      const ad=a.due_date||"9999",bd=b.due_date||"9999";
      if(ad!==bd)return ad.localeCompare(bd);
      return (a.title||"").localeCompare(b.title||"");
    });
    state.contacts=activeRows(changes,"office_contacts").sort((a,b)=>(a.name||"").localeCompare(b.name||""));
    state.notes=activeRows(changes,"notebook_entries").sort((a,b)=>(b.entry_date||"").localeCompare(a.entry_date||""));
    state.clientCreds=activeRows(changes,"client_credentials").sort((a,b)=>(a.credential_type||"").localeCompare(b.credential_type||""));
    state.officeCreds=activeRows(changes,"office_credentials").sort((a,b)=>(a.account_label||"").localeCompare(b.account_label||""));
    const when=data.server_time||new Date().toISOString();
    saveLastSync(when);
    $("machineLabel").textContent="Machine "+creds.machine_id+" · read-only";
    $("syncStatus").textContent=formatSyncLabel(when);
    render();
  }catch(err){
    const last=loadLastSync();
    $("syncStatus").className="status error";
    $("syncStatus").textContent=String(err.message||err)+(last?" · "+formatSyncLabel(last):"");
  }
}
`;
