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
`;
