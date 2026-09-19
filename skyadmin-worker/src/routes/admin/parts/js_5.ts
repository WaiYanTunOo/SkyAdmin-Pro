export const getJsPart5 = (csrfToken: string) => `
  var btn=document.getElementById('genBtn');btn.disabled=true;btn.textContent='Signing...';
  var payload=Object.assign({mid:mid,days:days,price:priceForDays(days)},readGenerateSku());
  api('POST','/api/generate',payload).then(function(d){
    document.getElementById('license').textContent=d.license_key;
    document.getElementById('passcode').textContent=d.passcode;
    document.getElementById('result').style.display='block';
    var so=document.getElementById('skuOut');
    if(so)so.textContent='org='+(d.org_id||'')+' · sync='+d.sync_enabled+' · web='+d.web_enabled+' · drive='+d.drive_files_enabled+' · max_devices='+d.max_devices;
    btn.disabled=false;btn.textContent='Generate';
    showStatus('Generated!');
    return loadRecords();
  }).catch(function(e){alert('Failed: '+e.message);btn.disabled=false;btn.textContent='Generate';});
}

function renderRecords(){
  var q=(document.getElementById('search').value||'').toUpperCase();
  var box=document.getElementById('records');box.innerHTML='';
  var shown=0;
  for(var i=0;i<_recs.length;i++){
    var r=_recs[i];
    var mid=r.machine_id||'';
    if(q&&mid.indexOf(q)<0)continue;
    if(!matchesRecFilter(r))continue;
    shown++;
    var nonce=r.nonce||'';
    var key=r.license_key||'';
    var pass=r.passcode||'';
    var pkg=r.package_days;
    var exp=r.expires_at||'never';
    var price=r.price_thb||0;
    var ts=r.issued_at||'';
    var isRevoked=r.revoked;
    var isUsed=r.used;
    var isExpired=r.is_expired||(exp!=='never'&&parseExp(exp)&&parseExp(exp).getTime()<=Date.now());
    var tag=isRevoked?'<span class="tag rev">REVOKED</span>':isExpired?'<span class="tag exp">EXPIRED</span>':isUsed?'<span class="tag ok">ACTIVE</span>':'<span class="tag pend">PENDING</span>';
    var left=r.time_left||timeLeftText(exp,isUsed,isRevoked);
    var expLabel=r.expires_label||(exp==='never'?'Never expires':exp);
    var d=document.createElement('div');d.className='rec'+(isRevoked?' revoked':'');
    var pkgStr=(pkg===null||pkg===undefined)?'Unlimited':pkg+'d';
    d.innerHTML='<div class="row"><b>'+esc(mid)+'</b> '+tag+'</div>'+
      '<div class="row expiry '+expiryClass(exp,isRevoked)+'">'+left+'</div>'+
      '<div class="row">Expires: '+expLabel+' · '+pkgStr+(price?' · '+price+'\u0e3f':'')+' · Issued: '+ts+'</div>';
    var b=document.createElement('div');b.className='btns';
    b.appendChild(mkBtn('Copy key','gray',function(k){return function(){navigator.clipboard.writeText(k);showStatus('Copied');};}(key)));
    b.appendChild(mkBtn('Copy PC','gray',function(p){return function(){navigator.clipboard.writeText(p);showStatus('Copied');};}(pass)));
    appendQuickRenew(b, mid);
    if(!isRevoked)b.appendChild(mkBtn('Revoke','red',function(n){return function(){doRevoke(n);};}(nonce)));
    if(isRevoked)b.appendChild(mkBtn('Unrevoke','gray',function(n){return function(){doUnrevoke(n);};}(nonce)));
    d.appendChild(b);box.appendChild(d);
  }
  document.getElementById('cnt').textContent='('+shown+'/'+_recs.length+')';
  if(!box.children.length)box.innerHTML='<div class="hint">No records match this filter.</div>';
}

function renew(mid,days){
  styledConfirm('Generate a new '+days+'-day license for '+mid+'?').then(function(ok){if(!ok)return;
  var price=priceForDays(days);
  var payload=Object.assign({mid:mid,days:days,price:price},readGenerateSku());
  api('POST','/api/generate',payload).then(function(d){
    navigator.clipboard.writeText(d.license_key);
    showStatus(days+'d generated & copied');
    return loadRecords();
  }).catch(function(e){alert(e.message);});
  });
}

function purgeOldLicenses(){
  var days=parseInt(document.getElementById('purgeDays').value,10);
  if(!days||days<1||days>365){showStatus('Enter days 1–365');return;}
  styledConfirm('Archive and delete stale license records older than '+days+' days?\\n\\nActive licenses are kept.').then(function(ok){if(!ok)return;
  api('POST','/api/purge-licenses',{older_than_days:days}).then(function(d){
    document.getElementById('purgeResult').textContent='Cleared '+d.purged+' record(s), archived '+d.archived+'.';
    showStatus('Purged '+d.purged);
    return loadRecords();
  }).catch(function(e){alert(e.message);});
  });
}

function doRevoke(nonce){
  styledConfirm('Revoke this license?').then(function(ok){if(!ok)return;
  api('POST','/api/revoke',{nonce:nonce}).then(function(){
    showStatus('Revoked');
    return loadRecords();
  }).catch(function(e){alert(e.message);});
`;
