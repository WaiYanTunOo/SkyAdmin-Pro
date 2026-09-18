export const getJsPart4 = (csrfToken: string) => `
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
    var left=m.time_left||timeLeftText(exp, m.status==='active'||m.status==='unlimited'||m.status==='used_expired', m.status==='revoked');
    var div=document.createElement('div');div.className='mach';
    var pkg=m.package_days==null?'Unlimited':m.package_days+'d';
    div.innerHTML=
      '<div class="row"><span class="ttl">'+esc(mid)+'</span> '+machStatusTag(m.status)+'</div>'+
      '<div class="row expiry '+expiryClass(exp,m.status==='revoked')+'">'+left+'</div>'+
      '<div class="row">Expires: '+(m.expires_label||'—')+' · Package: '+pkg+
      (m.issued_at?' · Issued: '+m.issued_at:'')+
      ' · '+m.license_count+' license(s)</div>';
    var b=document.createElement('div');b.className='btns';
    appendUseMachineId(b, mid);
    appendRenewControls(b, mid);
    div.appendChild(b);box.appendChild(div);
  }
  document.getElementById('machCnt').textContent='('+shown+'/'+_machines.length+')';
  if(!box.children.length)box.innerHTML='<div class="hint">No machines match this filter.</div>';
}

function generate(){
  var mid=document.getElementById('mid').value.trim().toUpperCase();
  if(!mid||!/^[0-9A-F]{16}$/.test(mid)){showStatus('Enter 16-hex Machine ID');return;}
  var sel=document.getElementById('days').value;
  var days;
  if(sel==='__custom__'){days=parseInt(document.getElementById('cDays').value);if(!days||days<1){showStatus('Enter days');return;}}
  else if(sel===''){days=null;}
  else days=parseInt(sel);
`;
