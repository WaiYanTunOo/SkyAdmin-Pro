export const getJsPart7 = (csrfToken: string) => `
  document.getElementById('machSearch').addEventListener('input',function(){renderMachines();});
  document.getElementById('search').addEventListener('input',function(){renderRecords();});
  var mfBtns=document.querySelectorAll('[data-mf]');
  for(var i=0;i<mfBtns.length;i++){
    mfBtns[i].addEventListener('click',function(){setMachFilter(this.getAttribute('data-mf'));});
  }
  var rfBtns=document.querySelectorAll('[data-rf]');
  for(var i=0;i<rfBtns.length;i++){
    rfBtns[i].addEventListener('click',function(){setRecFilter(this.getAttribute('data-rf'));});
  }
  document.getElementById('genKeysBtn').addEventListener('click', async function(){
    try {
      var kp = await crypto.subtle.generateKey({name:'Ed25519'}, true, ['sign','verify']);
      var pkcs8 = await crypto.subtle.exportKey('pkcs8', kp.privateKey);
      var raw = await crypto.subtle.exportKey('raw', kp.publicKey);

      var p8b64 = btoa(String.fromCharCode.apply(null, new Uint8Array(pkcs8)));
      var pem = '-----BEGIN PRIVATE KEY-----\\n' + (p8b64.match(/.{1,64}/g)||[]).join('\\n') + '\\n-----END PRIVATE KEY-----\\n';
      var wSec = btoa(pem);
      var hPub = Array.from(new Uint8Array(raw)).map(function(b){return b.toString(16).padStart(2,'0')}).join('');

      document.getElementById('sysKeysOut').style.display='block';
      document.getElementById('privKeyOut').value=wSec;
      document.getElementById('pubKeyOut').textContent=hPub;
      showStatus('Keys generated successfully');
    } catch(e) {
      alert('Error generating keys. Browser may not support WebCrypto Ed25519.\\n'+e);
    }
  });
}
if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',initDashboard);
}else{
  initDashboard();
}
`;
