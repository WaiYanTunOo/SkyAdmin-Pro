export const getJsPart0 = (csrfToken: string) => `
var CSRF_TOKEN=${JSON.stringify(csrfToken)};
var _recs=[];
var _machines=[];
var _bans=[];
var _packages=[];
var _tickTimer=null;
var _machFilter='all';
var _recFilter='all';

function esc(s){var d=document.createElement('div');d.appendChild(document.createTextNode(s));return d.innerHTML;}

function styledConfirm(msg){
  return new Promise(function(resolve){
    var overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center';
    var box=document.createElement('div');
    box.style.cssText='background:#1f2937;border:1px solid #374151;border-radius:14px;padding:24px;max-width:360px;width:90%;text-align:center';
    box.innerHTML='<div style="font-size:14px;margin-bottom:16px;color:#f9fafb;line-height:1.5">'+esc(msg)+'</div>';
    var btnRow=document.createElement('div');
    btnRow.style.cssText='display:flex;gap:8px;justify-content:center';
    var cancelBtn=document.createElement('button');
    cancelBtn.type='button';cancelBtn.textContent='Cancel';
    cancelBtn.style.cssText='padding:10px 20px;border:1px solid #4b5563;border-radius:8px;background:#374151;color:#e5e7eb;font-size:13px;font-weight:600;cursor:pointer';
    cancelBtn.onclick=function(){overlay.remove();resolve(false);};
    var okBtn=document.createElement('button');
    okBtn.type='button';okBtn.textContent='Confirm';
    okBtn.style.cssText='padding:10px 20px;border:0;border-radius:8px;background:#dc2626;color:white;font-size:13px;font-weight:600;cursor:pointer';
    okBtn.onclick=function(){overlay.remove();resolve(true);};
    btnRow.appendChild(cancelBtn);btnRow.appendChild(okBtn);
    box.appendChild(btnRow);overlay.appendChild(box);
    overlay.addEventListener('click',function(e){if(e.target===overlay){overlay.remove();resolve(false);}});
    document.body.appendChild(overlay);
  });
}

function showStatus(m){
  var s=document.getElementById('status');s.textContent=m;s.style.display='block';
  setTimeout(function(){s.style.display='none';},2000);
}

function showApiError(msg){
  var el=document.getElementById('apiBanner');
  el.textContent='API error: '+msg;
  el.style.display='block';
}

function api(method,path,body){
  // Session-cookie auth (HttpOnly, SameSite=Lax): the browser sends it
  // automatically same-origin. POSTs additionally carry the short-lived
  // X-CSRF-Token the server requires (see authMiddleware).
  var init={method:method,headers:{'Content-Type':'application/json','X-CSRF-Token':CSRF_TOKEN},credentials:'same-origin'};
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
    document.getElementById('apiBanner').style.display='none';
  }).catch(function(e){console.error('loadRecords:',e);showApiError('Records: '+e.message);});
}
function loadBans(){
  return api('GET','/api/bans').then(function(d){_bans=d.bans||[];renderBans();}).catch(function(e){console.error('loadBans:',e);showApiError('Bans: '+e.message);});
}

function fmtBaht(n){return Number(n||0).toLocaleString();}

var DEFAULT_PACKAGES=[
  {label:'1 Day',days:1,price_thb:50},
  {label:'7 Days',days:7,price_thb:500},
  {label:'30 Days',days:30,price_thb:800},
  {label:'1 Year',days:365,price_thb:9000}
];

function mkBtn(t,c,f){var x=document.createElement('button');x.type='button';x.className='sm '+c;x.textContent=t;x.addEventListener('click',f);return x;}

function updatePackageViews(){
  renderPackageSummary();
  renderPackageEditor();
  buildDaysSelect();
`;
