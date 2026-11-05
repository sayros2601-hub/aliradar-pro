(function(){
  'use strict';
  const $=id=>document.getElementById(id);
  const mobileLayout=matchMedia('(max-width: 1100px), (max-height: 480px) and (pointer: coarse)');
  const parts=[
    {key:'face',name:'Экран и безель',copy:'Передний модуль с синим циферблатом выходит из корпуса целиком. Экран соединяется с основной платой внутри.',where:'Устанавливается в передний проём корпуса.',dx:-.67,dy:.17,z:4},
    {key:'board',name:'Основная плата',copy:'Под экраном расположена электроника: микросхемы, контакты и разъёмы для остальных узлов.',where:'Внутри корпуса, за экраном.',dx:-.34,dy:.085,z:3},
    {key:'battery',name:'Аккумулятор',copy:'Тонкий аккумулятор питает часы. При разборе он выходит отдельным слоем между электроникой и корпусом.',where:'Во внутренней полости корпуса, подключается к плате.',dx:-.04,dy:0,z:2},
    {key:'body',name:'Корпус и браслет',copy:'Серебристый корпус, металлические звенья и две боковые кнопки остаются узнаваемыми. В открытом корпусе видно место для внутренних узлов.',where:'Основа сборки: остальные слои входят в передний проём.',dx:.28,dy:-.065,z:1}
  ];
  const root=document.createElement('div');root.className='watch-live';root.hidden=true;root.setAttribute('aria-label','Разбор часов на главной сцене');
  root.innerHTML='<svg class="watch-guide" viewBox="0 0 1000 1000" aria-hidden="true"><path d="M-300 590L700 330" fill="none" stroke="currentColor" stroke-dasharray="3 9"/></svg>';
  const layers=parts.map((part,i)=>{
    const layer=document.createElement('div');layer.className='watch-layer watch-layer-'+part.key;layer.style.zIndex=part.z;
    const img=new Image();img.dataset.src='assets/images/watch-layers/'+part.key+'.webp';img.alt=part.name;img.draggable=false;layer.append(img);
    const pin=document.createElement('button');pin.className='watch-layer-pin';pin.textContent=String(i+1).padStart(2,'0');pin.setAttribute('aria-label',part.name);pin.addEventListener('click',()=>select(i));layer.append(pin);root.append(layer);return layer;
  });
  $('product-stage').append(root);
  const controls=document.createElement('div');controls.id='watch-inline-controls';controls.hidden=true;
  controls.innerHTML='<div class="watch-inline-parts" aria-label="Узлы часов"></div><label class="watch-inline-range"><span>Разбор</span><input type="range" min="0" max="100" value="100" aria-label="Степень разборки часов"><output>100%</output></label><p class="watch-inline-location" aria-live="polite"></p><p class="watch-inline-note">Внутренние узлы показаны условно.</p>';
  $('watch-explode-button').after(controls);
  const chips=parts.map((p,i)=>{const b=document.createElement('button');b.textContent=String(i+1).padStart(2,'0')+' '+p.name;b.setAttribute('aria-pressed','false');b.addEventListener('click',()=>select(i));controls.querySelector('.watch-inline-parts').append(b);return b;});
  let amount=0,frame=0,stage=null,opened=false,saved=null,epoch=0,loading=false,loadAttempt=0;
  const range=controls.querySelector('input'),button=$('watch-explode-button');
  function select(index){
    layers.forEach((layer,i)=>{layer.classList.toggle('selected',i===index);layer.querySelector('button').setAttribute('aria-pressed',String(i===index));chips[i].setAttribute('aria-pressed',String(i===index));});
    if(opened){$('product-name').textContent=parts[index].name;$('product-description').textContent=parts[index].copy;controls.querySelector('.watch-inline-location').textContent=parts[index].where;}
  }
  function resize(){const bounds=$('product-stage').getBoundingClientRect();const size=Math.min(bounds.width*.85,bounds.height*.95);root.style.width=size+'px';root.style.height=size+'px';draw(amount);}
  function draw(value){
    amount=value;const mobile=mobileLayout.matches;const scale=1-(mobile?.43:.32)*value;
    root.style.transform=`translate(-50%, -50%) translateX(${value*(mobile?11:7)}%) scale(${scale})`;
    layers.forEach((layer,i)=>{layer.style.transform=`translate(${parts[i].dx*value*100}%,${parts[i].dy*value*100}%)`;});
    root.querySelector('.watch-guide').style.opacity=value*.3;
    root.style.opacity=Math.min(1,value*8);
    $('product-stage').style.setProperty('--watch-original-opacity',String(1-Math.min(1,value*8)));
    root.classList.toggle('labels-visible',value>.7);range.value=Math.round(value*100);controls.querySelector('output').textContent=Math.round(value*100)+'%';
    root.dataset.amount=String(Math.round(value*100));
  }
  function animate(target){
    cancelAnimationFrame(frame);const from=amount,start=performance.now();const quiet=document.body.classList.contains('is-reduced')||matchMedia('(prefers-reduced-motion: reduce)').matches;const duration=quiet?0:1550;
    function tick(now){const t=duration?Math.min(1,(now-start)/duration):1;const eased=t*t*(3-2*t);draw(from+(target-from)*eased);if(t<1)frame=requestAnimationFrame(tick);else if(!target)reset();}
    frame=requestAnimationFrame(tick);
  }
  function reset(){
    const restoreFocus=controls.contains(document.activeElement)||root.contains(document.activeElement);
    epoch++;cancelAnimationFrame(frame);opened=false;loading=false;amount=0;root.hidden=true;controls.hidden=true;button.disabled=false;button.textContent='Разобрать часы';button.setAttribute('aria-expanded','false');
    document.body.classList.remove('watch-is-open');$('product-stage').classList.remove('watch-is-exploding');$('product-stage').style.removeProperty('--watch-original-opacity');
    if(saved){$('product-name').textContent=saved.name;$('product-description').textContent=saved.copy;saved=null;}
    if(stage)stage.setPaused(false);
    if(restoreFocus)button.focus({preventScroll:true});
  }
  async function toggle(theStage){
    stage=theStage;if(loading)return;if(opened){animate(0);return;}
    const token=++epoch;loading=true;button.disabled=true;button.textContent='Подготовка деталей…';
    loadAttempt++;
    let loadTimer;
    try{
      const images=layers.map(layer=>{
        const img=layer.querySelector('img');
        if(!img.complete||!img.naturalWidth)img.src=img.dataset.src+(loadAttempt>1?'?retry='+loadAttempt:'');
        return img.decode();
      });
      await Promise.race([Promise.all(images),new Promise((_,reject)=>{loadTimer=setTimeout(()=>reject(new Error('Image timeout')),12000);})]);
    }catch(_){if(token===epoch){loading=false;button.disabled=false;button.textContent='Повторить загрузку деталей';}return;}
    finally{clearTimeout(loadTimer);}
    if(token!==epoch)return;
    loading=false;button.disabled=false;opened=true;saved={name:$('product-name').textContent,copy:$('product-description').textContent};stage.setPaused(true);
    root.hidden=false;controls.hidden=false;document.body.classList.add('watch-is-open');$('product-stage').classList.add('watch-is-exploding');button.textContent='Собрать часы';button.setAttribute('aria-expanded','true');
    resize();select(0);animate(1);
    if(mobileLayout.matches){
      const quiet=document.body.classList.contains('is-reduced')||matchMedia('(prefers-reduced-motion: reduce)').matches;
      $('product-stage').scrollIntoView({block:'start',behavior:quiet?'auto':'smooth'});
    }
  }
  range.addEventListener('input',()=>{cancelAnimationFrame(frame);draw(Number(range.value)/100);});
  window.addEventListener('resize',resize);
  window.addEventListener('keydown',e=>{if(e.key==='Escape'&&opened&&!document.querySelector('dialog[open]')){e.preventDefault();animate(0);}});
  button.removeAttribute('aria-haspopup');button.setAttribute('aria-controls',controls.id);button.setAttribute('aria-expanded','false');button.textContent='Разобрать часы';
  window.MiraWatch={toggle,reset,get active(){return opened;}};
})();
