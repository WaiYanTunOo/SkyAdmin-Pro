export const getJsPart6 = (csrfToken: string) => `
  });
}
function doUnrevoke(nonce){
  api('POST','/api/unrevoke',{nonce:nonce}).then(function(){
    showStatus('Un-revoked');
    return loadRecords();
  }).catch(function(e){alert(e.message);});
}

function loadUpdateInfo(){
  return fetch('/api/update',{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(d){
    if(!d.ok)return;
    if(d.version)document.getElementById('updVer').value=d.version;
    if(d.url)document.getElementById('updUrl').value=d.url;
    var st=document.getElementById('updStatus');
    st.textContent=d.version?'Current: v'+d.version+(d.url?' → '+d.url:''):'No update published yet.';
  }).catch(function(){});
}

function publishUpdate(){
  var version=(document.getElementById('updVer').value||'').trim();
  var url=(document.getElementById('updUrl').value||'').trim();
  if(!version){showStatus('Enter a version number.');return;}
  api('POST','/api/update',{version:version,url:url}).then(function(d){
    showStatus('Update published');
    document.getElementById('updStatus').textContent='Published v'+version+(url?' → '+url:'');
  }).catch(function(e){alert('Publish failed: '+e.message);});
}

function addBan(){
  var mid=document.getElementById('banIn').value.trim().toUpperCase();
  if(!/^[0-9A-F]{16}$/.test(mid)){showStatus('Enter 16 hex characters');return;}
  api('POST','/api/ban',{mid:mid}).then(function(){
    document.getElementById('banIn').value='';
    showStatus('Banned');
    return loadBans();
  }).catch(function(e){alert(e.message);});
}

function renderBans(){
  var box=document.getElementById('banList');box.innerHTML='';
  if(!_bans.length){box.innerHTML='<div class="hint">No bans.</div>';return;}
  for(var i=0;i<_bans.length;i++){
    var b=_bans[i];var m=b.machine_id;
    (function(m){
      var c=document.createElement('span');c.className='chip';c.textContent=m+' ';
      var x=document.createElement('button');x.textContent='\u2715';x.addEventListener('click',function(){
        api('POST','/api/unban',{mid:m}).then(function(){
          showStatus('Unbanned');
          loadBans();
        }).catch(function(e){alert(e.message);});
      });c.appendChild(x);box.appendChild(c);
    })(m);
  }
}

function copyEl(id){navigator.clipboard.writeText(document.getElementById(id).textContent);showStatus('Copied');}

_packages=DEFAULT_PACKAGES.slice();
updatePackageViews();
loadPricing().then(function(){
  setMachFilter('all');setRecFilter('all');
  loadUpdateInfo();
  loadRecords();loadBans();checkSigningKey();checkWorkerConfig();
});

document.addEventListener('DOMContentLoaded',function(){
  document.getElementById('addPkgBtn').addEventListener('click',function(){addPackageRow();});
  document.getElementById('savePkgBtn').addEventListener('click',function(){savePricing();});
  document.getElementById('reloadPkgBtn').addEventListener('click',function(){loadPricing(true);});
  document.getElementById('days').addEventListener('change',function(){
    document.getElementById('cWrap').style.display=this.value==='__custom__'?'block':'none';
  });
  document.getElementById('genBtn').addEventListener('click',function(){generate();});
  document.getElementById('copyKeyBtn').addEventListener('click',function(){copyEl('license');});
  document.getElementById('copyPassBtn').addEventListener('click',function(){copyEl('passcode');});
  document.getElementById('publishBtn').addEventListener('click',function(){publishUpdate();});
  document.getElementById('reloadUpdBtn').addEventListener('click',function(){loadUpdateInfo();});
  document.getElementById('banBtn').addEventListener('click',function(){addBan();});
  document.getElementById('purgeBtn').addEventListener('click',function(){purgeOldLicenses();});
`;
