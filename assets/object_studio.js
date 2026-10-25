/* Progressive photo presentation. Original photos and links are never replaced. */
(() => {
  'use strict';
  const source=document.getElementById('products-db');if(!source)return;
  const {copy:C}=JSON.parse(source.textContent);
  const reduce=matchMedia('(prefers-reduced-motion: reduce)'),fine=matchMedia('(hover:hover) and (pointer:fine)');
  const paused=()=>reduce.matches || document.documentElement.dataset.motion==='off';
  let active=null,frame=0;
  function clear(){if(active){active.style.removeProperty('--rx');active.style.removeProperty('--ry');active.style.removeProperty('--lx');active.style.removeProperty('--ly');active.removeAttribute('data-hover');}active=null;cancelAnimationFrame(frame);frame=0;}
  document.addEventListener('pointermove',event=>{
    if(paused()||!fine.matches)return;
    const target=event.target.closest('.card-image,.studio-photo,.exhibit-photo,.modal-photo');
    if(!target){if(active)clear();return;}
    if(active!==target){clear();active=target;}
    const x=event.clientX,y=event.clientY;
    cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{
      const r=target.getBoundingClientRect();
      const sx=Math.max(0,Math.min(1,(x-r.left)/r.width)),sy=Math.max(0,Math.min(1,(y-r.top)/r.height));
      target.style.setProperty('--rx',`${(0.5-sy)*7}deg`);target.style.setProperty('--ry',`${(sx-.5)*9}deg`);
      target.style.setProperty('--lx',`${sx*100}%`);target.style.setProperty('--ly',`${sy*100}%`);target.dataset.hover='true';frame=0;
    });
  },{passive:true});
  document.addEventListener('pointerout',event=>{if(active&&!active.contains(event.relatedTarget))clear();},{passive:true});
  document.addEventListener('visibilitychange',clear);reduce.addEventListener('change',clear);
  document.getElementById('motion-toggle')?.addEventListener('click',clear);
  const seen=new WeakSet();
  const observer='IntersectionObserver' in window?new IntersectionObserver(entries=>{
    for(const entry of entries){entry.target.dataset.inView=String(entry.isIntersecting);if(entry.isIntersecting&&!seen.has(entry.target)){seen.add(entry.target);entry.target.dataset.arrived='true';}}
  },{threshold:.12}):null;
  function observe(root){if(!observer)return;for(const e of root.querySelectorAll('.product-card,.studio-stage,.vault-exhibit,.journal-grid article')){if(e.dataset.observed)continue;e.dataset.observed='true';observer.observe(e);}}
  observe(document);
  const grid=document.getElementById('product-grid');
  if(grid)new MutationObserver(()=>observe(grid)).observe(grid,{childList:true});
  // Native dialog preserves keyboard focus, escape and a usable full-image link.
  const viewer=document.createElement('dialog');viewer.id='image-viewer';viewer.setAttribute('aria-label',C.image_open);
  const toolbar=document.createElement('div');toolbar.className='image-viewer-toolbar';
  const note=document.createElement('span');note.textContent=C.image_note;
  const zoom=document.createElement('button');zoom.type='button';zoom.textContent='＋';zoom.setAttribute('aria-label',C.image_zoom);zoom.setAttribute('aria-pressed','false');
  const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label',C.image_close);
  toolbar.append(note,zoom,close);
  const viewport=document.createElement('div');viewport.className='image-viewer-viewport';
  const photo=document.createElement('img');viewport.append(photo);viewer.append(toolbar,viewport);document.body.append(viewer);
  let trigger=null,oldOverflow='';
  function dismiss(){viewer.close();document.body.style.overflow=oldOverflow;viewer.dataset.zoomed='false';zoom.setAttribute('aria-pressed','false');trigger?.focus({preventScroll:true});}
  close.addEventListener('click',dismiss);viewer.addEventListener('cancel',e=>{e.preventDefault();dismiss();});
  viewer.addEventListener('click',e=>{if(e.target===viewer){const r=viewer.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dismiss();}});
  zoom.addEventListener('click',()=>{const on=viewer.dataset.zoomed!=='true';viewer.dataset.zoomed=String(on);zoom.setAttribute('aria-pressed',String(on));});
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-enlarge]');if(!button)return;
    event.preventDefault();trigger=button;photo.src=button.dataset.enlarge;photo.alt=button.dataset.imageTitle||'';
    oldOverflow=document.body.style.overflow;document.body.style.overflow='hidden';viewer.dataset.zoomed='false';viewer.showModal();close.focus();
  });
  document.addEventListener('keydown',event=>{
    if(event.key!=='/'||event.ctrlKey||event.metaKey||event.altKey||event.isComposing||event.target.closest('input,textarea,select,[contenteditable=true],dialog'))return;
    const input=document.getElementById('global-search-input');if(input){event.preventDefault();input.focus();}
  });
})();
