export const getJsPart1 = (csrfToken: string) => `
  var n=_packages.filter(function(p){return p.days!==null;}).length;
  document.getElementById('pkgStatus').textContent=n?n+' package(s) ready for Generate and renew buttons.':'No packages — add rows below.';
  if(document.getElementById('machines').children.length||_machines.length)renderMachines();
  if(document.getElementById('records').children.length||_recs.length)renderRecords();
}

function renderPackageSummary(){
  var box=document.getElementById('pkgSummary');
  box.innerHTML='';
  var shown=0;
  for(var i=0;i<_packages.length;i++){
    var p=_packages[i];
    if(p.days===null) continue;
    shown++;
    var item=document.createElement('div');
    item.className='item';
    item.innerHTML='<span><b>'+esc(p.label)+'</b> · '+p.days+' day'+(p.days===1?'':'s')+'</span><span class="price">'+fmtBaht(p.price_thb)+' Baht</span>';
    box.appendChild(item);
  }
  if(!shown) box.innerHTML='<div class="hint" style="padding:4px 0">No packages loaded yet.</div>';
}

function appendUseMachineId(container, mid){
  var btn=mkBtn('Use ID','gray',function(id){
    return function(){
      document.getElementById('mid').value=id;
      document.getElementById('mid').scrollIntoView({behavior:'smooth',block:'center'});
      showStatus('Machine ID filled (Fill MID)');
    };
  }(mid));
  btn.title='Fill MID — copy this Machine ID into Generate License above';
  container.appendChild(btn);
}

function appendQuickRenew(container, mid){
  if(_packages.length){
    for(var i=0;i<_packages.length;i++){
      var p=_packages[i];
      if(p.days===null) continue;
      (function(d){
        container.appendChild(mkBtn('+'+d+'d','green',function(m,dd){return function(){renew(m,dd);};}(mid,d)));
      })(p.days);
    }
  } else {
    container.appendChild(mkBtn('+7d','green',function(m){return function(){renew(m,7);};}(mid)));
    container.appendChild(mkBtn('+30d','green',function(m){return function(){renew(m,30);};}(mid)));
  }
}

function appendRenewControls(container, mid){
  appendQuickRenew(container, mid);
  var wrap=document.createElement('span');
  wrap.className='renew-custom';
  var inp=document.createElement('input');
  inp.type='number';
  inp.min='1';
  inp.max='36500';
  inp.placeholder='Days';
  inp.className='renew-days';
  inp.title='Custom renewal length in days';
  wrap.appendChild(inp);
  wrap.appendChild(mkBtn('Renew','green',function(m,input){
    return function(){
      var days=parseInt(input.value,10);
      if(!days||days<1){alert('Enter days (1–36500)');input.focus();return;}
      renew(m,days);
    };
  }(mid,inp)));
  container.appendChild(wrap);
}

function buildDaysSelect(){
  var sel=document.getElementById('days');
  sel.innerHTML='';
  for(var i=0;i<_packages.length;i++){
    var p=_packages[i];
    if(p.days===null) continue;
    var opt=document.createElement('option');
    opt.value=String(p.days);
    opt.textContent=esc(p.label)+' \u2014 '+fmtBaht(p.price_thb)+' Baht';
`;
