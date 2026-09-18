export const getJsPart4 = () => `
function b64ToBytes(s){
  const pad="=".repeat((4-(s.length%4))%4);
  const bin=atob((s+pad).replace(/-/g,"+").replace(/_/g,"/"));
  const out=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++)out[i]=bin.charCodeAt(i);
  return out;
}

async function deriveVaultKey(passphrase,saltBytes){
  const enc=new TextEncoder();
  const base=await crypto.subtle.importKey("raw",enc.encode(passphrase),{name:"PBKDF2"},false,["deriveKey"]);
  return crypto.subtle.deriveKey(
    {name:"PBKDF2",salt:saltBytes,iterations:PBKDF2_ITERS,hash:"SHA-256"},
    base,
    {name:"AES-GCM",length:256},
    false,
    ["decrypt"]
  );
}

async function decryptVsk1(cipher,passphrase){
  if(!cipher||!String(cipher).startsWith(VAULT_PREFIX))return "";
  try{
    const raw=b64ToBytes(String(cipher).slice(VAULT_PREFIX.length));
    if(raw.length<16+12+16)return "";
    const salt=raw.slice(0,16);
    const nonce=raw.slice(16,28);
    const ct=raw.slice(28);
    const key=await deriveVaultKey(passphrase,salt);
    const plain=await crypto.subtle.decrypt({name:"AES-GCM",iv:nonce},key,ct);
    return new TextDecoder().decode(plain);
  }catch{return ""}
}

function lockVault(){
  state.vaultKey=null;
  if(state.vaultTimer){clearTimeout(state.vaultTimer);state.vaultTimer=null}
  if(state.tab==="passwords")renderPasswords();
}

function bumpVaultIdle(){
  if(!state.vaultKey)return;
  if(state.vaultTimer)clearTimeout(state.vaultTimer);
  state.vaultTimer=setTimeout(lockVault,VAULT_IDLE_MS);
}

function openVaultModal(){
  $("vaultUnlock").classList.remove("hidden");
  $("vaultPhrase").value="";
  $("vaultUnlockStatus").textContent="";
  $("vaultPhrase").focus();
}

function closeVaultModal(){ $("vaultUnlock").classList.add("hidden") }

async function tryUnlockVault(){
  const phrase=($("vaultPhrase").value||"").trim();
  const status=$("vaultUnlockStatus");
  if(state.vaultFail>=5){
    status.className="status error";
    status.textContent="Too many attempts — wait and try again.";
    return;
  }
  if(phrase.length<8){
    status.className="status error";
    status.textContent="Passphrase too short.";
    return;
  }
  const sample=[...state.clientCreds,...state.officeCreds].map(r=>r.secret_value).find(v=>v&&String(v).startsWith(VAULT_PREFIX));
  if(!sample){
    status.className="status error";
    status.textContent="No synced ciphertext yet — set passphrase on desktop and Sync Now.";
    return;
  }
  const plain=await decryptVsk1(sample,phrase);
  if(!plain){
    state.vaultFail+=1;
    status.className="status error";
    status.textContent="Wrong passphrase.";
    return;
  }
  state.vaultFail=0;
  state.vaultKey=phrase;
  bumpVaultIdle();
  closeVaultModal();
  renderPasswords();
}

function wireVaultUi(){
  $("btnVaultUnlock").addEventListener("click",tryUnlockVault);
  $("btnVaultCancel").addEventListener("click",closeVaultModal);
  $("vaultPhrase").addEventListener("keydown",e=>{if(e.key==="Enter")tryUnlockVault()});
  document.addEventListener("pointerdown",bumpVaultIdle);
  document.addEventListener("keydown",bumpVaultIdle);
}

async function copyText(text){
  try{await navigator.clipboard.writeText(text||"")}catch{}
}

function renderPasswords(){
  const el=$("panel-passwords");
  const unlocked=!!state.vaultKey;
  const q=($("search").value||"").trim();
  const cFields=["credential_type","login_id","username","portal_url","registration_number","notes"];
  const oFields=["account_label","login_id","email","system_type","portal_url","notes"];
  const clientRows=state.clientCreds.filter(r=>matchSearch(r,cFields));
  const officeRows=state.officeCreds.filter(r=>matchSearch(r,oFields));
  const lockbar='<div class="lockbar">'+(unlocked
    ?'<button type="button" class="secondary" id="btnVaultLock">Lock</button><span class="status">Unlocked · auto-locks after idle</span>'
    :'<button type="button" id="btnVaultOpen">Unlock</button><span class="status">Passwords locked — metadata only</span>')+'</div>';
  if(!clientRows.length&&!officeRows.length){
    el.innerHTML=lockbar+emptyHtml(q?"No passwords match":"No portal logins yet",q?"Try another search.":"Sync from desktop after setting Mobile Vault Passphrase.");
    wirePasswordButtons();
    return;
  }
  const clientHtml=clientRows.map((r,i)=>{
    const client=clientName(r.client_global_id);
    const login=r.login_id||r.username||r.registration_number||"";
    const hasCt=r.secret_value&&String(r.secret_value).startsWith(VAULT_PREFIX);
    return '<article class="card" data-kind="client" data-idx="'+i+'"><h3>'+esc(client||"Client")+'</h3><div class="meta"><span class="badge">'+esc(r.credential_type||"Portal")+'</span>'+
      (login?'<span class="badge">'+esc(login)+'</span>':"")+(hasCt?'':'<span class="badge">No password synced</span>')+'</div>'+
      (r.portal_url?'<div class="meta">'+esc(r.portal_url)+'</div>':"")+
      '<div class="secret meta" data-secret>'+(unlocked&&hasCt?'••••••••':'🔒 locked')+'</div>'+
      (unlocked&&hasCt?'<div class="btn-row"><button type="button" data-act="reveal">Reveal</button><button type="button" class="secondary" data-act="copy">Copy</button></div>':"")+
      '</article>';
  }).join("");
  const officeHtml=officeRows.map((r,i)=>{
    const login=r.login_id||r.email||"";
    const hasCt=r.secret_value&&String(r.secret_value).startsWith(VAULT_PREFIX);
    return '<article class="card" data-kind="office" data-idx="'+i+'"><h3>'+esc(r.account_label||"Office")+'</h3><div class="meta"><span class="badge">'+esc(r.system_type||"Account")+'</span>'+
      (login?'<span class="badge">'+esc(login)+'</span>':"")+(hasCt?'':'<span class="badge">No password synced</span>')+'</div>'+
      (r.portal_url?'<div class="meta">'+esc(r.portal_url)+'</div>':"")+
      '<div class="secret meta" data-secret>'+(unlocked&&hasCt?'••••••••':'🔒 locked')+'</div>'+
      (unlocked&&hasCt?'<div class="btn-row"><button type="button" data-act="reveal">Reveal</button><button type="button" class="secondary" data-act="copy">Copy</button></div>':"")+
      '</article>';
  }).join("");
  el.innerHTML=lockbar+(clientRows.length?'<h3 class="meta" style="margin:8px 0">Client portals</h3>':"")+clientHtml+
    (officeRows.length?'<h3 class="meta" style="margin:16px 0 8px">Office accounts</h3>':"")+officeHtml;
  wirePasswordButtons();
}

function wirePasswordButtons(){
  const open=$("btnVaultOpen"); if(open)open.onclick=openVaultModal;
  const lock=$("btnVaultLock"); if(lock)lock.onclick=lockVault;
  $("panel-passwords").querySelectorAll("article.card").forEach(card=>{
    const kind=card.dataset.kind;
    const idx=Number(card.dataset.idx);
    const cFields=["credential_type","login_id","username","portal_url","registration_number","notes"];
    const oFields=["account_label","login_id","email","system_type","portal_url","notes"];
    const rows=kind==="client"?state.clientCreds.filter(r=>matchSearch(r,cFields)):state.officeCreds.filter(r=>matchSearch(r,oFields));
    const row=rows[idx];
    card.querySelectorAll("[data-act]").forEach(btn=>{
      btn.onclick=async()=>{
        bumpVaultIdle();
        if(!state.vaultKey||!row)return;
        const plain=await decryptVsk1(row.secret_value,state.vaultKey);
        if(!plain){lockVault();return}
        if(btn.dataset.act==="copy"){await copyText(plain);btn.textContent="Copied";setTimeout(()=>btn.textContent="Copy",1200)}
        if(btn.dataset.act==="reveal"){const s=card.querySelector("[data-secret]");if(s)s.textContent=plain}
      };
    });
  });
}
`;
