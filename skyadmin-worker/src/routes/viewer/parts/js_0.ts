export const getJsPart0 = (tables: string) => `
const STORAGE_KEY="skyadmin_viewer_creds";
const VIEWER_TABLES=${JSON.stringify(tables)};
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
`;
