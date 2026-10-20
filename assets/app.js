(() => {
  'use strict';
  const state = JSON.parse(document.getElementById('signal-data').textContent);
  const { edition, prefix } = state;
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pretty = value => new Date(value + 'T12:00:00Z').toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric',timeZone:'UTC'});
  const toast = text => { const box = $('.toast'); box.textContent=text;box.hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>box.hidden=true,3500); };
  let lastFocus;
  function openDialog(dialog) { lastFocus=document.activeElement; dialog.showModal(); dialog.scrollTop=0; dialog.querySelector('.close').focus(); }
  $$('dialog').forEach(dialog => {
    dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
    dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
    dialog.addEventListener('close',()=>lastFocus?.focus());
  });
  $$('[data-dialog]').forEach(button=>button.addEventListener('click',()=>{openDialog(document.getElementById(button.dataset.dialog)); if(button.dataset.dialog==='catchup-dialog')catchup();}));
  $$('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
    $$('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    const filter=button.dataset.filter;
    $('.world-grid-section').hidden=filter==='frontiers'||!$('.world-grid-section .story-card');
    $('#frontiers').hidden=filter==='world'||!$('#frontiers .story-card');
    if($('.more-section'))$('.more-section').hidden=filter==='frontiers'||!$('.more-section .more-item');
    const lead=$('.lead-story');
    if(lead)lead.hidden=filter!=='all'&&lead.dataset.section!==filter;
    if($('.atlas'))$('.atlas').hidden=filter==='frontiers';
  }));
  $$('.navlinks a').forEach(link=>link.addEventListener('click',()=>{if(location.pathname===new URL(link.href).pathname && (link.hash==='#frontiers'||link.hash==='#ai-frontier'||link.hash==='#regions'))$('[data-filter=all]')?.click();}));
  $$('[data-mode]').forEach(button=>button.addEventListener('click',()=>{
    $$('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    document.body.classList.toggle('quick',button.dataset.mode==='quick');
  }));
  $('#share-edition')?.addEventListener('click',async()=>{
    const url=new URL(`${prefix}editions/${edition.date}/`,location.href).href;
    try {await navigator.clipboard.writeText(url);toast('Edition link copied.');}
    catch {toast('Copy this edition’s link from your address bar.');}
  });
  const progress=()=>{const max=document.documentElement.scrollHeight-innerHeight;$('.progress').style.width=(max>0?Math.min(100,scrollY/max*100):0)+'%';};
  addEventListener('scroll',progress,{passive:true});addEventListener('resize',progress);progress();
  const note=$('#stale-note');
  if(note && !location.pathname.includes('/editions/')){
    const age=Date.now()-new Date(edition.cutoff).getTime();
    if(age>40*3600000){note.hidden=false;note.textContent=`The latest published edition is ${pretty(edition.date)}. This page is an edition, not a live news feed.`;}
  }
  // Catch me up: choose how long you were away; stories are grouped by thread, biggest first.
  const VISIT_KEY='hetgetij:lastVisit';
  const readVisit=()=>{try{return Number(localStorage.getItem(VISIT_KEY))||0;}catch{return 0;}};
  const writeVisit=()=>{try{localStorage.setItem(VISIT_KEY,String(Date.now()));}catch{}};
  const lastVisit=readVisit();
  const awayDays=lastVisit?Math.floor((Date.now()-lastVisit)/86400000):null;
  writeVisit();
  const RANGES=[1,3,7,14,30];
  let choice=awayDays==null?'7':String(RANGES.find(n=>n>=Math.max(1,awayDays))||30);
  const welcomeText=awayDays>=2?`Welcome back. You were last here ${awayDays} days ago.`:'';
  const banner=$('#welcome-back');
  if(banner&&welcomeText&&!location.pathname.includes('/editions/')){banner.hidden=false;banner.querySelector('span').textContent=welcomeText;}
  if(welcomeText){const w=$('#catchup-welcome');w.hidden=false;w.textContent=welcomeText+' Here is what changed.';}
  const dayDiff=(a,b)=>Math.round((new Date(a+'T12:00:00Z')-new Date(b+'T12:00:00Z'))/86400000);
  const WEIGHT={world:3,still:2,ai:2,frontiers:2,more:1};
  const sectionName=s=>s==='ai'||s==='frontiers'?'Frontiers':s==='more'?'More that changed':s==='still'?'Still matters':'World';
  function groupThreads(list,latestDate){
    const groups=new Map();
    list.forEach(ed=>ed.stories.forEach(s=>{
      if(!groups.has(s.h))groups.set(s.h,{h:s.h,items:[],score:0});
      const g=groups.get(s.h);g.items.push({date:ed.date,story:s});
      g.score+=(WEIGHT[s.s]||1)+(s.l?4:0)+(ed.date===latestDate?1:0);
    }));
    const w=i=>(WEIGHT[i.story.s]||1)+(i.story.l?4:0);
    groups.forEach(g=>g.items.sort((a,b)=>a.date===b.date?w(a)-w(b):(a.date<b.date?-1:1)));
    return [...groups.values()].sort((a,b)=>b.score-a.score||(b.items.at(-1).date>a.items.at(-1).date?1:-1));
  }
  function threadCard(g,primer){
    const last=g.items.at(-1),s=last.story,n=g.items.length;
    const earlier=g.items.slice(0,-1).reverse();
    const older=earlier.length?`<details class="cu-earlier"><summary>${earlier.length} more report${earlier.length>1?'s':''}</summary>${earlier.map(i=>`<p><small>${escape(pretty(i.date))}</small> <strong>${escape(i.story.t)}.</strong> ${escape(i.story.w)}</p>`).join('')}</details>`:'';
    const meta=primer?sectionName(s.s):`${sectionName(s.s)} · ${n} report${n>1?'s':''}`;
    const lead=primer&&s.hs?`<p class="cu-summary">${escape(s.hs)}</p>`:'';
    return `<article class="cu-thread"><span class="eyebrow">${escape(meta)}</span><h3><a href="${prefix}threads/${encodeURIComponent(g.h)}/">${escape(s.ht)} ↗</a></h3>${lead}<p class="cu-latest"><small>${escape(pretty(last.date))}</small> <a href="${prefix}stories/${encodeURIComponent(s.id)}/">${escape(s.t)}</a>. ${escape(s.u||s.w)}</p>${older}</article>`;
  }
  let dataPromise, request=0;
  async function catchup(){
    const ticket=++request,target=$('#catchup-results');
    $$('[data-days]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.days===choice)));
    target.innerHTML='<p>Gathering the stories…</p>';
    try{
      dataPromise ||= fetch(prefix+'data/catchup.json').then(r=>{if(!r.ok)throw Error('Unavailable');return r.json();});
      const data=await dataPromise;if(ticket!==request)return;
      const latestDate=data.latest;
      if(choice==='new'){
        const list=data.editions.filter(x=>dayDiff(latestDate,x.date)<14);
        const top=groupThreads(list,latestDate).slice(0,6);
        target.innerHTML='<p class="cu-intro">New here? These are the biggest stories we’re following. Each one opens a timeline of everything we’ve reported on it.</p>'+top.map(g=>threadCard(g,true)).join('');
        return;
      }
      const days=Number(choice);
      const list=data.editions.filter(x=>dayDiff(latestDate,x.date)<days);
      if(!list.length){target.innerHTML='<h3>You’re up to date.</h3><p>Nothing new has been published in that time.</p>';return;}
      const groups=groupThreads(list,latestDate),shown=groups.slice(0,10),rest=groups.slice(10);
      const young=dayDiff(latestDate,data.first)+1<days?` Het Getij began on ${escape(pretty(data.first))}, so this covers everything so far.`:'';
      const intro=`<p class="cu-intro">${list.length} edition${list.length>1?'s':''} · ${groups.length} stor${groups.length>1?'ies':'y'}, biggest first.${young}</p>`;
      const more=rest.length?`<details class="cu-more"><summary>${rest.length} more stor${rest.length>1?'ies':'y'}</summary>${rest.map(g=>threadCard(g,false)).join('')}</details>`:'';
      target.innerHTML=intro+shown.map(g=>threadCard(g,false)).join('')+more;
    }catch{dataPromise=null;target.innerHTML=`<p>The catch-up view could not load. <a href="${prefix}archive/"><u>Browse the archive instead →</u></a></p>`;}
  }
  $$('[data-days]').forEach(b=>b.addEventListener('click',()=>{choice=b.dataset.days;catchup();}));

  // Regions: the numbered map markers and the chips below it select a region panel.
  const regionLinks=$$('[data-region]');
  function selectRegion(slug,reveal){
    regionLinks.forEach(link=>{
      const active=link.dataset.region===slug;
      link.classList.toggle('is-active',active);
      if(active)link.setAttribute('aria-current','true');else link.removeAttribute('aria-current');
    });
    $$('[data-panel]').forEach(panel=>panel.hidden=panel.dataset.panel!==slug);
    const panel=document.getElementById('region-panel-'+slug);
    if(reveal&&panel&&matchMedia('(max-width:760px)').matches)panel.scrollIntoView({behavior:'smooth',block:'start'});
  }
  regionLinks.forEach(link=>link.addEventListener('click',event=>{event.preventDefault();selectRegion(link.dataset.region,true);}));
  if(regionLinks.length)selectRegion(regionLinks[0].dataset.region,false);
})();
