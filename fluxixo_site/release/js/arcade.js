(() => {
  'use strict';
  const labels={en:'Next find',ru:'Новая находка',pt:'Novo achado',es:'Otro hallazgo',fr:'À découvrir',he:'התגלית הבאה'};
  const about = document.getElementById('about-button');
  const mobileAbout = document.createElement('button');
  mobileAbout.className = 'arcade-mobile-about';
  mobileAbout.textContent = 'i';
  mobileAbout.setAttribute('aria-haspopup','dialog');
  mobileAbout.addEventListener('click',()=>about.click());
  document.querySelector('.explorer-footer').append(mobileAbout);
  const update=()=>{const lang=document.documentElement.lang.split('-')[0];document.querySelector('.spin-label').textContent=labels[lang]||labels.en;mobileAbout.setAttribute('aria-label',about.getAttribute('aria-label')||'About FLUXIXO');};
  update();
  new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
})();
