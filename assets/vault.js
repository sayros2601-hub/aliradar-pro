/* Native scroll, an optional progressive WebGL sculpture and a product exhibit.
   The document, product links and hero environment are usable before this runs. */
(() => {
  'use strict';
  const world=document.querySelector('.vault-world');
  if(!world)return;
  const journey=document.querySelector('.vault-journey');
  const reduce=matchMedia('(prefers-reduced-motion: reduce)');
  const coarse=matchMedia('(pointer: coarse)');
  let visible=true, mode=0, px=0, py=0, frame=0, gl=null, draw=null, time=0, previous=0, scrollQueued=false;
  const paused=()=>reduce.matches || document.documentElement.dataset.motion==='off';
  const canvas=document.getElementById('vault-canvas');
  const core=canvas.parentElement;
  function scrollScene(){
    scrollQueued=false;
    const box=journey.getBoundingClientRect();
    const progress=Math.max(0,Math.min(1,-box.top/Math.max(1,journey.offsetHeight-innerHeight)));
    world.style.setProperty('--travel',paused()?0:progress);
    document.body.dataset.scrolled=String(scrollY>60);
  }
  addEventListener('scroll',()=>{if(!scrollQueued){scrollQueued=true;requestAnimationFrame(scrollScene);}},{passive:true});
  world.addEventListener('pointermove',event=>{
    if(paused()||coarse.matches)return;
    const r=world.getBoundingClientRect();
    px=(event.clientX-r.left)/r.width-.5;py=(event.clientY-r.top)/r.height-.5;
    world.style.setProperty('--mx',px);world.style.setProperty('--my',py);
  },{passive:true});
  world.addEventListener('pointerleave',()=>{px=py=0;world.style.setProperty('--mx',0);world.style.setProperty('--my',0);});
  world.querySelectorAll('[data-scene]').forEach(button=>button.addEventListener('click',()=>{
    mode=Number(button.dataset.scene);world.dataset.scene=String(mode);
    world.querySelectorAll('[data-scene]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    draw?.();
  }));
  function tick(now){
    frame=0;
    if(!visible||document.hidden||paused()||!draw)return;
    // Bound the effect to 24fps and <230k pixels, independent of display DPI.
    if(now-previous>=1000/24){time+=Math.min((now-previous)/1000,.08);previous=now;draw();}
    frame=requestAnimationFrame(tick);
  }
  function sync(){
    cancelAnimationFrame(frame);frame=0;previous=performance.now();scrollScene();
    if(paused()){px=py=0;world.style.setProperty('--mx',0);world.style.setProperty('--my',0);draw?.();}
    else if(visible&&!document.hidden&&draw)frame=requestAnimationFrame(tick);
  }
  if('IntersectionObserver' in window)new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();}).observe(world);
  document.addEventListener('visibilitychange',sync);reduce.addEventListener('change',sync);
  document.getElementById('motion-toggle')?.addEventListener('click',sync);
  function setup(){
    if(document.hidden)return;
    try{
      gl=canvas.getContext('webgl',{alpha:true,antialias:false,depth:false,powerPreference:'low-power',premultipliedAlpha:false});
      if(!gl)return;
      const vertex=`attribute vec2 position;void main(){gl_Position=vec4(position,0.,1.);}`;
      const fragment=`precision highp float;
uniform vec2 resolution;uniform float clock;uniform vec2 pointer;uniform float mode;
mat2 rot(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}
float shape(vec3 p){
 p.xz=rot(clock*.19+pointer.x*.9)*p.xz;p.yz=rot(.38+pointer.y*.6)*p.yz;
 if(mode<.5){p.xy=rot(p.z*.38)*p.xy;return length(vec2(length(p.xy)-.82,p.z))-.24;}
 if(mode<1.5){p.xy=rot(.6+clock*.09)*p.xy;return (abs(p.x)+abs(p.y)+abs(p.z)-1.12)*.57735-.065;}
 p.yz=rot(.75)*p.yz;
 float a=length(vec2(length(p.xy)-.76,p.z))-.13;
 float b=length(vec2(length(p.yz)-.76,p.x))-.13;
 return min(a,b);
}
vec3 normal(vec3 p){vec2 e=vec2(.002,0.);return normalize(vec3(shape(p+e.xyy)-shape(p-e.xyy),shape(p+e.yxy)-shape(p-e.yxy),shape(p+e.yyx)-shape(p-e.yyx)));}
vec3 environment(vec3 r){
 vec3 dark=vec3(.035,.075,.14),light=vec3(.65,.82,1.);
 vec3 c=mix(dark,light,smoothstep(-.45,.9,r.y));
 float softbox=pow(max(0.,1.-abs(r.x*.75+r.y*.4-.35)),25.);
 float strip=pow(max(0.,1.-abs(r.x-r.z*.7+.45)),45.);
 c+=vec3(.92,.96,1.)*softbox*1.4+vec3(.24,.5,.94)*strip;
 c*=.28+.72*smoothstep(-.25,.05,r.y);
 return c;
}
void main(){
 vec2 uv=(gl_FragCoord.xy-.5*resolution)/resolution.y;
 vec3 ro=vec3(0.,0.,4.2),rd=normalize(vec3(uv*3.3,-4.));
 float t=0.;bool hit=false;
 for(int i=0;i<58;i++){vec3 p=ro+rd*t;float d=shape(p);if(d<.002){hit=true;break;}t+=d*.83;if(t>7.)break;}
 if(!hit){gl_FragColor=vec4(0.);return;}
 vec3 p=ro+rd*t,n=normal(p),r=reflect(rd,n);
 float fres=pow(1.-max(0.,dot(n,-rd)),3.);
 vec3 c=environment(r)*(.75+fres*.6);
 float diffuse=max(dot(n,normalize(vec3(-2.,3.,4.))),0.);
 c+=vec3(.12,.19,.28)*diffuse;
 c+=vec3(.45,.7,1.)*pow(max(dot(r,normalize(vec3(-1.,2.,2.))),0.),55.)*2.;
 if(mode>0.5&&mode<1.5)c=mix(c,c*vec3(1.17,.92,1.3),.4);
 if(mode>1.5)c=mix(c,c*vec3(.6,1.25,1.1),.45);
 c=pow(c,vec3(.82));gl_FragColor=vec4(c,1.);
}`;
      function compile(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error('Sculpture shader unavailable');return s;}
      const program=gl.createProgram();const vs=compile(gl.VERTEX_SHADER,vertex),fs=compile(gl.FRAGMENT_SHADER,fragment);
      gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);
      if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('Sculpture unavailable');
      gl.useProgram(program);
      const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
      const loc=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
      const uniforms={};for(const name of ['resolution','clock','pointer','mode'])uniforms[name]=gl.getUniformLocation(program,name);
      const resize=()=>{const r=core.getBoundingClientRect();const size=Math.round(Math.min(480,Math.max(200,r.width)));canvas.width=size;canvas.height=size;gl.viewport(0,0,size,size);draw?.();};
      draw=()=>{if(gl.isContextLost())return;gl.uniform2f(uniforms.resolution,canvas.width,canvas.height);gl.uniform1f(uniforms.clock,time);gl.uniform2f(uniforms.pointer,px,py);gl.uniform1f(uniforms.mode,mode);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);};
      resize();core.dataset.ready='true';
      addEventListener('resize',()=>{resize();scrollScene();},{passive:true});sync();
      canvas.addEventListener('webglcontextlost',()=>{cancelAnimationFrame(frame);draw=null;core.dataset.ready='false';});
    }catch{core.dataset.ready='false';draw=null;}
  }
  // Defer optional rendering until first content has painted.
  if('requestIdleCallback' in window)requestIdleCallback(setup,{timeout:1500});else setTimeout(setup,350);
  scrollScene();
  const next=document.getElementById('exhibit-next');
  next?.addEventListener('click',()=>{
    const source=document.getElementById('hero-candidates'),link=document.querySelector('[data-hero-id]');
    if(!source||!link)return;
    let products;try{products=JSON.parse(source.textContent);}catch{return;}
    if(!products.length)return;
    const index=products.findIndex(p=>p.id===link.dataset.heroId),item=products[(index+1)%products.length];
    const img=link.querySelector('img'),title=link.querySelector('.spotlight-bottom>span');
    link.href=item.href;link.dataset.heroId=item.id;img.src=item.image;img.alt=item.title;title.textContent=item.title;title.title=item.title;
  });
})();
