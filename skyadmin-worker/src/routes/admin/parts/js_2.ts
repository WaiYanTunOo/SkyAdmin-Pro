export const getJsPart2 = (csrfToken: string) => `
    if(p.days===7) opt.selected=true;
    sel.appendChild(opt);
  }
  var custom=document.createElement('option');
  custom.value='__custom__'; custom.textContent='Custom days...';
  sel.appendChild(custom);
  var never=document.createElement('option');
  never.value=''; never.textContent='Never (owner)';
  sel.appendChild(never);
}

function readPackageRows(){
  var rows=document.querySelectorAll('#pkgEditor .pkg-row');
  var out=[];
  for(var i=0;i<rows.length;i++){
    var row=rows[i];
    var label=(row.querySelector('.pkg-label')||{}).value||'';
    var days=parseInt((row.querySelector('.pkg-days')||{}).value,10);
    var price=parseInt((row.querySelector('.pkg-price')||{}).value,10);
    if(!label||!days||days<1) continue;
    out.push({label:label.trim(),days:days,price_thb:isNaN(price)?0:price});
  }
  return out;
}

function renderPackageEditor(){
  var box=document.getElementById('pkgEditor');
  box.innerHTML='';
  for(var i=0;i<_packages.length;i++){
    if(_packages[i].days===null) continue;
    addPackageRow(_packages[i]);
  }
}

function addPackageRow(pkg){
  pkg=pkg||{label:'',days:30,price_thb:0};
  var box=document.getElementById('pkgEditor');
  var row=document.createElement('div');
  row.className='pkg-row';
  row.innerHTML=
    '<input class="pkg-label" placeholder="Label" value="'+esc(pkg.label||'')+'">'+
    '<input class="pkg-days" type="number" min="1" max="36500" placeholder="Days" value="'+(pkg.days||'')+'">'+
    '<input class="pkg-price" type="number" min="0" placeholder="Baht" value="'+(pkg.price_thb||0)+'">'+
    '<button type="button" class="sm red del-row-btn">Del</button>';
  row.querySelector('.del-row-btn').addEventListener('click',function(){row.remove();});
  box.appendChild(row);
}

function loadPricing(showToast){
  return fetch('/api/pricing',{credentials:'same-origin'})
    .then(function(r){
      if(!r.ok) throw new Error('pricing HTTP '+r.status);
      return r.json();
    })
    .then(function(d){
      if(!d.ok) throw new Error(d.error||'pricing failed');
      _packages=Array.isArray(d.packages)?d.packages:[];
      if(!_packages.length) _packages=DEFAULT_PACKAGES.slice();
      document.getElementById('overYear').value=d.over_year_text||'';
      updatePackageViews();
      if(showToast) showStatus('Packages reloaded');
    })
    .catch(function(e){
      console.error('loadPricing:',e);
      if(!_packages.length) _packages=DEFAULT_PACKAGES.slice();
      updatePackageViews();
      document.getElementById('pkgStatus').textContent='Could not load packages from server — showing defaults. Tap Reload to retry.';
      if(showToast) showStatus('Using default packages');
    });
}

function savePricing(){
  var packages=readPackageRows();
  if(!packages.length){showStatus('Add at least one package.');return;}
  api('POST','/api/pricing',{
    packages:packages,
    over_year_text:document.getElementById('overYear').value.trim()
  }).then(function(d){
    _packages=d.packages||packages;
    updatePackageViews();
`;
