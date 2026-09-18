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
});
`;
