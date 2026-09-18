export const getJsPart3 = (csrfToken: string) => `
    showStatus('Packages saved');
  }).catch(function(e){alert('Save failed: '+e.message);});
}

function priceForDays(days){
  for(var i=0;i<_packages.length;i++){
    if(_packages[i].days===days) return _packages[i].price_thb||0;
  }
  return 0;
}

function checkSigningKey(){
  fetch('/api/signing/public-key',{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(d){
    if(!d.ok) return;
    var el=document.getElementById('keyBanner');
    if(!d.matches_desktop){
      el.style.display='block';
      el.textContent='WARNING: Worker signing key does NOT match the desktop app. Activation codes will fail until LICENSE_ED25519_PRIVATE_KEY_B64 matches license_public.py (client key '+d.client_public_key_hex.slice(0,8)+'…).';
    }
  }).catch(function(){});
}

function checkWorkerConfig(){
  fetch('/api/signing/public-key',{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(d){
    if(!d.ok){
      showApiError('Worker signing key not configured - license generation will fail. Run: npx wrangler secret put LICENSE_ED25519_PRIVATE_KEY_B64');
    }
  }).catch(function(e){showApiError('Cannot reach Worker: '+e.message);});
}

function parseExp(exp){
  if(!exp||exp==='never')return null;
  var t=String(exp);
  var d=new Date(t.endsWith('Z')?t:t+'Z');
  return isNaN(d.getTime())?null:d;
}

function timeLeftText(exp, used, revoked){
  if(revoked)return 'Revoked';
  var d=parseExp(exp);
  if(!d)return used?'Unlimited (activated)':'Unlimited (pending)';
  var ms=d.getTime()-Date.now();
  if(ms<=0){
    var ago=Math.abs(ms), days=Math.floor(ago/86400000), hrs=Math.floor((ago%86400000)/3600000);
    if(days>0)return 'Expired '+days+'d'+(hrs?' '+hrs+'h':'')+' ago';
    if(hrs>0)return 'Expired '+hrs+'h ago';
    return 'Expired';
  }
  var days=Math.floor(ms/86400000), hrs=Math.floor((ms%86400000)/3600000), mins=Math.floor((ms%3600000)/60000);
  var left='';
  if(days>0)left=days+'d'+(hrs?' '+hrs+'h':'');
  else if(hrs>0)left=hrs+'h'+(mins?' '+mins+'m':'');
  else left=Math.max(mins,1)+'m';
  return left+' left'+(used?'':' to activate');
}

function expiryClass(exp, revoked){
  if(revoked)return 'expired';
  var d=parseExp(exp);
  if(!d)return 'pending';
  return d.getTime()<=Date.now()?'expired':'';
}

function machStatusTag(st){
  var map={active:'ok',pending:'pend',expired:'exp',used_expired:'exp',revoked:'rev',unlimited:'ok',none:'rev'};
  var lbl={active:'ACTIVE',pending:'PENDING',expired:'EXPIRED',used_expired:'USED+EXPIRED',revoked:'REVOKED',unlimited:'UNLIMITED',none:'NONE'};
  return '<span class="tag '+(map[st]||'rev')+'">'+(lbl[st]||st.toUpperCase())+'</span>';
}

function setMachFilter(f){
  _machFilter=f;
  var btns=document.querySelectorAll('[data-mf]');
  for(var i=0;i<btns.length;i++){
    btns[i].className='sm gray'+(btns[i].getAttribute('data-mf')===f?' on':'');
  }
  renderMachines();
}
function setRecFilter(f){
  _recFilter=f;
  var btns=document.querySelectorAll('[data-rf]');
  for(var i=0;i<btns.length;i++){
    btns[i].className='sm gray'+(btns[i].getAttribute('data-rf')===f?' on':'');
  }
  renderRecords();
}

function matchesMachFilter(m){
  if(_machFilter==='all')return true;
`;
