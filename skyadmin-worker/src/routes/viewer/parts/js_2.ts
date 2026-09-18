export const getJsPart2 = () => `
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
`;
