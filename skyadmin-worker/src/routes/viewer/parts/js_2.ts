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

function groupInfo(gid){
  if(!gid)return null;
  return state.groups.find(r=>r.global_id===gid)||null;
}

function renderGroups(){
  const el=$("panel-groups");
  const q=($("search").value||"").trim();
  const rows=state.groups.filter(r=>matchSearch(r,["name","color"]));
  if(!rows.length){
    el.innerHTML=emptyHtml(q?"No groups match":"No groups yet",q?"Try another search.":"Sync from desktop to populate groups.");
    return;
  }
  el.innerHTML=rows.map(r=>{
    const count=state.clients.filter(c=>c.group_global_id===r.global_id).length;
    const sw=r.color?'<span class="swatch" style="background:'+esc(r.color)+'"></span>':"";
    return '<article class="card"><h3>'+sw+esc(r.name||"Group")+'</h3><div class="meta"><span class="badge">'+count+' client'+(count===1?"":"s")+'</span></div></article>';
  }).join("");
}

function renderClients(){
  const el=$("panel-clients");
  const q=($("search").value||"").trim();
  const rows=state.clients.filter(r=>matchSearch(r,["name","company_name","contact_name","email","status","service_type","contact_number","notes","tax_id","registration_number"]));
  if(!rows.length){
    el.innerHTML=emptyHtml(q?"No clients match":"No clients yet",q?"Try another search.":"Sync from desktop to populate clients.");
    return;
  }
  el.innerHTML=rows.map(r=>{
    const g=groupInfo(r.group_global_id);
    const gBadge=g?(g.color?'<span class="swatch" style="background:'+esc(g.color)+'"></span>':"")+'<span class="badge">'+esc(g.name)+'</span>':"";
    return '<article class="card"><h3>'+esc(r.name)+'</h3><div class="meta"><span class="badge">'+esc(r.status||"active")+'</span>'+
      (r.service_type?'<span class="badge">'+esc(r.service_type)+'</span>':"")+
      (r.payment_status?'<span class="badge">'+esc(r.payment_status)+'</span>':"")+gBadge+'</div>'+
      [r.company_name,r.contact_name,r.tax_id&&("Tax ID "+r.tax_id),r.registration_number&&("Reg "+r.registration_number),r.contact_number&&("📞 "+r.contact_number),r.email&&("✉ "+r.email)].filter(Boolean).map(x=>'<div class="meta">'+esc(x)+'</div>').join("")+
      (r.notes?'<div class="body">'+esc(r.notes)+'</div>':"")+'</article>';
  }).join("");
}

function renderTasks(){
  const el=$("panel-tasks");
  const q=($("search").value||"").trim();
  const rows=state.tasks.filter(r=>matchSearch(r,["title","description","category","status","due_date","pipeline_step"]));
  if(!rows.length){
    el.innerHTML=emptyHtml(q?"No tasks match":"No tasks yet",q?"Try another search.":"Sync from desktop to populate tasks.");
    return;
  }
  el.innerHTML=rows.map(r=>{
    const client=clientName(r.client_global_id);
    const done=r.status==="completed";
    return '<article class="card"><h3>'+(done?"✓ ":"")+esc(r.title)+'</h3><div class="meta"><span class="badge">'+esc(TASK_STATUS[r.status]||r.status||"Task")+'</span>'+
      (r.category?'<span class="badge">'+esc(r.category)+'</span>':"")+
      (r.pipeline_step?'<span class="badge">'+esc(r.pipeline_step)+'</span>':"")+
      (client?'<span class="badge">'+esc(client)+'</span>':"")+'</div>'+
      '<div class="row2 meta">'+(r.due_date?"Due "+esc(r.due_date):"")+(r.completed_at?(r.due_date?" · ":"")+"Done "+esc(r.completed_at):"")+'</div>'+
      (r.description?'<div class="body">'+esc(r.description)+'</div>':"")+'</article>';
  }).join("");
}
`;
