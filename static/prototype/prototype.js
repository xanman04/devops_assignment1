/* Standalone desktop interaction prototype. No API requests or account writes. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const icon = name => `<svg aria-hidden="true"><use href="#${name}"/></svg>`;
  const initial = {page:'near', x:0, y:0, zoom:1, genres:[], match:'any', date:'Next two weeks', from:'', to:'', tracked:false};
  let saved;
  try { saved = JSON.parse(sessionStorage.getItem('music-ui-prototype') || '{}'); } catch { saved = {}; }
  const state = {...initial, ...saved};
  const colors = ['#72aaff','#dcab61','#b697d7','#6db8a1','#d38f9e','#a3b56b'];
  const genres = colors.map((color,index) => ({id:String(index), name:`Genre ${String(index+1).padStart(2,'0')}`, color}));
  let draftGenres = [], draftMatch = 'any', dateChoice = state.date, toastTimer;
  const save = () => { try { sessionStorage.setItem('music-ui-prototype', JSON.stringify(state)); } catch { /* File previews may disable storage. */ } };
  function toast(text) {
    $('#toast').textContent = text; $('#toast').hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 3500);
  }
  function open(id) {
    if (id === '#detail-dialog') {
      if (!$(id).open) $(id).show();
    } else {
      $(id).showModal();
    }
  }
  $$('[data-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  $$('dialog').forEach(dialog => dialog.addEventListener('click', event => {
    const box = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
  }));

  // An invented street drawing keeps the mockup self-contained and avoids map services.
  const ns = 'http://www.w3.org/2000/svg', city = $('#city-map');
  function draw(tag, attributes) {
    const node = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key,value]) => node.setAttribute(key,value));
    city.append(node); return node;
  }
  draw('rect',{width:1600,height:1100,fill:'#292c2f'});
  const park = 'M210 190 370 145 450 260 385 385 210 350Z';
  draw('path',{d:park,fill:'#303633'});
  draw('path',{d:'M1150 690 1450 620 1510 900 1240 975Z',fill:'#303633'});
  for (let row=0;row<15;row++) {
    for (let column=0;column<20;column++) {
      const x=column*83+20, y=row*78+10;
      if ((column*7+row*3)%11 === 0) continue;
      const inset=(column+row)%3*3;
      draw('rect',{x:x+inset,y:y+inset,width:58-inset,height:49-inset,rx:2,
        fill:(row+column)%4 === 0 ? '#393c3f' : '#323538',transform:`rotate(${column<6?-12:column>14?14:0} ${x+30} ${y+25})`});
    }
  }
  for (let i=0;i<18;i++) {
    const x=60+i*86;
    draw('path',{d:`M${x-100} -50 L${x+15} 330 L${x} 650 L${x+100} 1150`,stroke:'#43474b','stroke-width':3});
  }
  for (let i=0;i<14;i++) {
    const y=40+i*79;
    draw('path',{d:`M-50 ${y+65} L490 ${y} L1010 ${y+12} L1650 ${y-45}`,stroke:'#45494c','stroke-width':3});
  }
  const river='M-100 760 C240 510 410 1020 730 790 S1180 350 1700 550';
  draw('path',{d:river,stroke:'#444a4e','stroke-width':83});
  draw('path',{d:river,stroke:'#23292f','stroke-width':67});
  const avenues=['M170 -100 960 1200','M-80 170 1630 965','M-60 860 1640 210','M1080 -80 440 1190'];
  avenues.forEach(d=>{draw('path',{d,stroke:'#25282b','stroke-width':20});draw('path',{d,stroke:'#575b5e','stroke-width':8});});
  draw('ellipse',{cx:835,cy:410,rx:165,ry:140,stroke:'#25282b','stroke-width':18});
  draw('ellipse',{cx:835,cy:410,rx:165,ry:140,stroke:'#55595b','stroke-width':7});
  draw('circle',{cx:835,cy:410,r:30,fill:'#303437',stroke:'#626668','stroke-width':6});

  function transformMap() {
    state.zoom = Math.max(.75, Math.min(2.2, Number(state.zoom) || 1));
    state.x = Math.max(-300, Math.min(300, Number(state.x) || 0));
    state.y = Math.max(-220, Math.min(220, Number(state.y) || 0));
    $('#map-world').style.transform = `translate(${state.x}px,${state.y}px) scale(${state.zoom})`;
  }
  transformMap();
  const surface = $('#map-surface'), pointers = new Map();
  let gesture = null, suppressClickUntil = 0;
  const clampZoom = value => Math.max(.75, Math.min(2.2, value));
  function mapPoint(x, y) {
    const rect=surface.getBoundingClientRect();
    return {x:x-rect.left-rect.width/2, y:y-rect.top-rect.height/2};
  }
  function pointerPair() {
    const [a,b]=[...pointers.values()];
    return {center:mapPoint((a.x+b.x)/2,(a.y+b.y)/2), distance:Math.hypot(a.x-b.x,a.y-b.y)};
  }
  function startGesture() {
    if (pointers.size>=2) {
      const pair=pointerPair();
      gesture={type:'pinch', distance:Math.max(1,pair.distance), zoom:state.zoom,
        anchor:{x:(pair.center.x-state.x)/state.zoom,y:(pair.center.y-state.y)/state.zoom}};
      suppressClickUntil=performance.now()+350;
    } else if (pointers.size===1) {
      const point=[...pointers.values()][0];
      gesture={type:'drag',x:point.x,y:point.y,baseX:state.x,baseY:state.y};
    } else gesture=null;
    surface.classList.toggle('dragging',pointers.size>0);
  }
  function zoomAt(point, zoom) {
    const anchor={x:(point.x-state.x)/state.zoom,y:(point.y-state.y)/state.zoom};
    state.zoom=clampZoom(zoom);
    state.x=point.x-anchor.x*state.zoom; state.y=point.y-anchor.y*state.zoom;
    transformMap();
  }
  surface.addEventListener('pointerdown', event => {
    const button=event.target.closest('button');
    if (event.button!==0 || (button && event.pointerType!=='touch')) return;
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
    (button || surface).setPointerCapture(event.pointerId);
    startGesture();
  });
  surface.addEventListener('pointermove', event => {
    if (!pointers.has(event.pointerId)) return;
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
    if (gesture.type==='pinch') {
      const pair=pointerPair();
      state.zoom=clampZoom(gesture.zoom*pair.distance/gesture.distance);
      state.x=pair.center.x-gesture.anchor.x*state.zoom;
      state.y=pair.center.y-gesture.anchor.y*state.zoom;
      suppressClickUntil=performance.now()+350;
    } else {
      const dx=event.clientX-gesture.x,dy=event.clientY-gesture.y;
      state.x=gesture.baseX+dx; state.y=gesture.baseY+dy;
      if (Math.hypot(dx,dy)>5) suppressClickUntil=performance.now()+350;
    }
    transformMap();
  });
  const stopGesture = event => {
    if (!pointers.delete(event.pointerId)) return;
    if (gesture.type==='pinch') suppressClickUntil=performance.now()+350;
    startGesture(); save();
  };
  ['pointerup','pointercancel','lostpointercapture'].forEach(name=>surface.addEventListener(name,stopGesture));
  surface.addEventListener('click',event=>{
    if (performance.now()<suppressClickUntil) {event.preventDefault();event.stopPropagation();}
  },true);
  // Desktop trackpad pinches arrive as Ctrl+wheel. Wheel zoom also works for a mouse.
  surface.addEventListener('wheel',event=>{
    event.preventDefault();
    const unit=event.deltaMode===1?16:event.deltaMode===2?surface.clientHeight:1;
    zoomAt(mapPoint(event.clientX,event.clientY),state.zoom*Math.exp(-event.deltaY*unit*(event.ctrlKey ? .01 : .002)));
    if (pointers.size) startGesture();
    save();
  },{passive:false});
  $('#zoom-in').onclick = () => {state.zoom+=.15;transformMap();save();};
  $('#zoom-out').onclick = () => {state.zoom-=.15;transformMap();save();};
  $('#recenter').onclick = () => {state.x=0;state.y=0;state.zoom=1;transformMap();save();};
  let selectedPin = 'one';
  const previews = {
    one: {title:'Event title A', venue:'Venue A', color:'#72aaff'},
    two: {title:'Event title B', venue:'Venue B', color:'#dcab61'},
    multiple: {title:'Event title C', venue:'Venue C', color:'#b697d7'},
  };
  function preview(multiple=false, title=null) {
    const info=previews[selectedPin];
    $('#detail-dialog').close();
    $('#single-preview h1').textContent=title || info.title;
    $('#single-preview .venue-line').textContent=info.venue;
    $('#single-preview .chip').style.setProperty('--accent',info.color);
    $('#multiple-preview h1').textContent=info.venue;
    $('#event-panel').style.setProperty('--event-accent',info.color);
    $('#detail-dialog h2').textContent=title || info.title;
    $('#detail-dialog > .muted').textContent=info.venue+' · Local date and time';
    $('#detail-dialog .chip').style.setProperty('--accent',info.color);
    $('#single-preview').hidden=multiple; $('#multiple-preview').hidden=!multiple;
    $('#panel-kicker').textContent=multiple ? '2 EVENTS · ONE VENUE' : 'EVENT'; $('#event-panel').hidden=false;
  }
  $$('.pin').forEach(pin=>pin.onclick=()=>{
    selectedPin=pin.dataset.pin;
    $$('.pin').forEach(p=>{p.classList.toggle('selected',p===pin);p.setAttribute('aria-pressed',String(p===pin));});
    preview(selectedPin==='multiple');
  });
  const closePreview=()=>{
    $('#event-panel').hidden=true;
    $$('.pin').forEach(p=>{p.classList.remove('selected');p.setAttribute('aria-pressed','false');});
  };
  $('#panel-close').onclick=closePreview;
  $$('#multiple-preview .venue-event').forEach((button,index)=>{
    button.firstChild.textContent=`Event title C${index+1} `;
    button.onclick=()=>preview(false,`Event title C${index+1}`);
  });
  $('#event-more').onclick=()=>open('#detail-dialog');
  $('#track-preview').onclick=()=>{
    state.tracked=!state.tracked; save();
    $('#track-preview').setAttribute('aria-pressed',String(state.tracked));
    $('#track-preview').textContent=state.tracked?'Tracking event':'Track event';
    if(state.page==='events')renderPage();
  };
  $('#track-preview').setAttribute('aria-pressed',String(state.tracked));
  $('#track-preview').textContent=state.tracked?'Tracking event':'Track event';
  $('#ticket-preview').onclick=()=>toast('An external ticket link would open here.');
  $('#groups-preview').onclick=()=>{$('#detail-dialog').close();location.hash='groups';};

  function updateFilters() {
    state.genres=Array.isArray(state.genres)?state.genres.filter(id=>/^[0-5](-[ab])?$/.test(id)):[];
    $('#date-summary').textContent=state.date;
    $('#filters-open span').textContent=state.genres.length?`Genres · ${state.genres.length} selected`:'All genres';
    $('#clear-selection').hidden=!state.genres.length;
    $('#selected-chips').replaceChildren();
    state.genres.slice(0,2).forEach(id=>{
      const genre=genres[Number(id[0])], chip=document.createElement('button');
      chip.className='chip';chip.style.setProperty('--accent',genre.color);
      chip.textContent=id.includes('-')?'Subgenre '+id.slice(-1).toUpperCase():genre.name;
      chip.title='Edit selected genres';chip.onclick=()=>$('#filters-open').click();$('#selected-chips').append(chip);
    });
    if(state.genres.length>2){const more=document.createElement('button');more.className='subtag';more.textContent=`+${state.genres.length-2}`;more.onclick=()=>$('#filters-open').click();$('#selected-chips').append(more);}
  }
  function drawFilters() {
    const query=$('#genre-search').value.toLowerCase();
    $('#genre-options').innerHTML=genres.filter(g=>`${g.name} subgenre`.toLowerCase().includes(query)).map(g=>`
      <div class="genre-row"><button class="chip" data-genre="${g.id}" style="--accent:${g.color}" aria-pressed="${draftGenres.includes(g.id)}">${g.name}</button>
      <button class="expand-tags" data-expand="${g.id}" aria-expanded="false" aria-label="Expand ${g.name}">+</button>
      <div class="subgenres" data-children="${g.id}" hidden>${['a','b'].map(letter=>`<button class="chip" data-genre="${g.id}-${letter}" style="--accent:${g.color}" aria-pressed="${draftGenres.includes(`${g.id}-${letter}`)}">Subgenre ${letter.toUpperCase()}</button>`).join('')}</div></div>`).join('');
    if(!$('#genre-options').children.length)$('#genre-options').textContent='No matching placeholder genres.';
    $$('#match-mode button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.match===draftMatch)));
  }
  $('#filters-open').onclick=()=>{draftGenres=[...state.genres];draftMatch=state.match;$('#genre-search').value='';drawFilters();open('#filter-dialog');};
  $('#genre-search').oninput=drawFilters;
  $('#genre-options').onclick=event=>{
    const chip=event.target.closest('[data-genre]'), expand=event.target.closest('[data-expand]');
    if(chip){const id=chip.dataset.genre;draftGenres=draftGenres.includes(id)?draftGenres.filter(g=>g!==id):[...draftGenres,id];chip.setAttribute('aria-pressed',String(draftGenres.includes(id)));}
    if(expand){const children=$(`[data-children="${expand.dataset.expand}"]`);children.hidden=!children.hidden;expand.textContent=children.hidden?'+':'−';expand.setAttribute('aria-expanded',String(!children.hidden));}
  };
  $$('#match-mode button').forEach(button=>button.onclick=()=>{draftMatch=button.dataset.match;$$('#match-mode button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));});
  $('#filter-clear').onclick=()=>{draftGenres=[];drawFilters();};
  $('#filter-apply').onclick=()=>{state.genres=[...draftGenres];state.match=draftMatch;save();updateFilters();$('#filter-dialog').close();};
  $('#clear-selection').onclick=()=>{state.genres=[];save();updateFilters();};
  $('#date-open').onclick=()=>{
    dateChoice=state.date;$('#date-from').value=state.from;$('#date-to').value=state.to;$('#date-error').hidden=true;
    $$('[data-date]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.date===dateChoice)));open('#date-dialog');
  };
  $$('[data-date]').forEach(button=>button.onclick=()=>{
    dateChoice=button.dataset.date;$('#date-from').value='';$('#date-to').value='';
    $$('[data-date]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  });
  $$('.date-range input').filter(input=>input.id.startsWith('date-')).forEach(input=>input.oninput=()=>{$$('[data-date]').forEach(b=>b.setAttribute('aria-pressed','false'));});
  $('#date-apply').onclick=()=>{
    const from=$('#date-from').value,to=$('#date-to').value;
    if((from||to)&&(!from||!to||to<from)){$('#date-error').hidden=false;return;}
    state.from=from;state.to=to;
    const format=value=>new Date(value+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric'});
    state.date=from?`${format(from)} – ${format(to)}`:dateChoice;
    save();updateFilters();$('#date-dialog').close();
  };
  updateFilters();
  $('#search-open').onclick=()=>open('#search-dialog');
  $('#global-search').oninput=event=>{
    $('#search-hint').textContent=event.target.value.trim()?'Search results would appear here. No data is connected in this prototype.':'Search across events, venues and artists.';
  };
  document.addEventListener('keydown',event=>{
    if(event.key==='/'&&!event.target.closest('input,textarea')&&!document.querySelector('dialog[open]')){event.preventDefault();open('#search-dialog');}
    if(event.key==='Escape') {
      if ($('#detail-dialog').open) $('#detail-dialog').close();
      else if (!document.querySelector('dialog[open]')) closePreview();
    }
  });
  $('#event-form').onsubmit=event=>{event.preventDefault();toast('Layout preview only. No event was created.');};

  const pageInfo={
    discover:{title:'Discover',intro:'Explore the music. Find what moves you.'},
    events:{title:'My events',intro:'The nights you’re keeping an eye on.'},
    groups:{title:'Groups',intro:'A little company for your next night out.'},
    profile:{title:'Profile',intro:'Your corner of the map.',icon:'profile'}
  };
  function renderPage() {
    const page=state.page, info=pageInfo[page];
    if(!info)return;
    const heading=`<div class="page-top"><div><p class="eyebrow">YOUR SPACE</p><h1>${info.title}</h1></div>${page==='events'?'<button class="primary" data-create>List an event <span>+</span></button>':''}</div><p class="muted page-intro">${info.intro}</p>`;
    if(page==='profile'){
      $('#content-page').innerHTML=heading+`<form class="profile-form"><span class="avatar">N</span><label>Username<input placeholder="Username" autocomplete="off"></label><label>Display name<input placeholder="How you’d like to appear" autocomplete="off"></label><label>Email (optional)<input type="email" placeholder="Only visible to you" autocomplete="off"></label><p class="muted">This is a layout preview; account changes aren’t saved.</p><button class="primary">Save changes</button></form>`;
      $('.profile-form').onsubmit=event=>{event.preventDefault();toast('Preview only. No account details were saved.');};return;
    }
    const sections={
      discover:[
        {id:'genres',title:'Genres',note:'Find a sound to explore',kind:'genre',name:'Genre',meta:'Explore the sound',symbol:'discover'},
        {id:'artists',title:'Artists',note:'Follow the music that catches your ear',kind:'artist',name:'Artist',meta:'Artist preview',symbol:'profile'},
        {id:'djs',title:'DJs',note:'Get to know the people behind the decks',kind:'artist',name:'DJ',meta:'Sets & listening references',symbol:'profile'},
        {id:'discover-events',title:'Events',note:'Explore beyond your current map view',kind:'event',name:'Event',meta:'Venue · Local date and time',symbol:'events'},
      ],
      events:[
        {id:'tracked',title:'Tracked events',note:state.tracked?'Your tracked preview appears first':'Nights you want to keep an eye on',kind:'event',name:'Event',meta:'Venue · Local date and time',symbol:'events'},
        {id:'listings',title:'Your listings',note:'The events you share with the community',kind:'event',name:'Listing',meta:'Venue · Local date and time',symbol:'events'},
      ],
      groups:[
        {id:'my-groups',title:'My groups',note:'People you’re planning to go with',kind:'group',name:'Group',meta:'Event · Group description',symbol:'groups'},
        {id:'requests',title:'Requests',note:'Keep up with your join requests',kind:'group',name:'Group request',meta:'Event · Request preview',symbol:'groups'},
      ],
    };
    const rows=sections[page].map(section=>{
      const cards=Array.from({length:6},(_,index)=>{
        const title=section.id==='tracked'&&index===0&&state.tracked?'Event title A':`${section.name} ${String(index+1).padStart(2,'0')}`;
        const status=section.id==='requests'?['Pending','Approved','Pending'][index%3]:section.id==='tracked'&&index===0&&state.tracked?'Tracking':'';
        return `<button class="browse-card ${section.kind}-card" data-card="${section.id}" data-card-title="${title}" style="--accent:${colors[index]}">
          <span class="card-art">${icon(section.symbol)}<span class="card-index">${String(index+1).padStart(2,'0')}</span>${status?`<span class="card-status">${status}</span>`:''}</span>
          <strong>${title}</strong><small>${section.meta}</small></button>`;
      }).join('');
      return `<section class="carousel-section" aria-labelledby="heading-${section.id}">
        <header class="carousel-heading"><div><h2 id="heading-${section.id}">${section.title}</h2><p>${section.note}</p></div>
          <div class="carousel-controls"><button data-scroll="${section.id}" data-direction="-1" aria-label="Previous ${section.title.toLowerCase()}" disabled>‹</button><button data-scroll="${section.id}" data-direction="1" aria-label="Next ${section.title.toLowerCase()}">›</button></div></header>
        <div class="carousel-track" id="row-${section.id}" tabindex="0" aria-label="${section.title} preview cards">${cards}</div></section>`;
    }).join('');
    $('#content-page').innerHTML=heading+rows;
    $$('.carousel-track').forEach(track=>{
      const update=()=>{
        $(`[data-scroll="${track.id.slice(4)}"][data-direction="-1"]`).disabled=track.scrollLeft<=1;
        $(`[data-scroll="${track.id.slice(4)}"][data-direction="1"]`).disabled=track.scrollLeft+track.clientWidth>=track.scrollWidth-1;
      };
      track.addEventListener('scroll',update); update();
    });
  }
  $('#content-page').onclick=event=>{
    const arrow=event.target.closest('[data-scroll]');
    if(arrow){const track=$(`#row-${arrow.dataset.scroll}`);track.scrollBy({left:Number(arrow.dataset.direction)*track.clientWidth*.8,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
    const card=event.target.closest('[data-card]');
    if(card){
      $('#card-title').textContent=card.dataset.cardTitle;
      $('#card-kind').textContent=card.closest('section').querySelector('h2').textContent;
      $('#card-description').textContent='This card previews the layout. Details, listening references, and actions for this item will appear here when connected.';
      open('#card-dialog');
    }
    if(event.target.closest('[data-create]'))open('#create-dialog');
  };
  $('#card-near').onclick=()=>$('#card-dialog').close();
  function route() {
    if ($('#detail-dialog').open) $('#detail-dialog').close();
    if ($('#card-dialog').open) $('#card-dialog').close();
    const page=location.hash.slice(1)||'near';state.page=page==='near'||Object.hasOwn(pageInfo,page)?page:'near';save();
    const near=state.page==='near';$('#near-page').hidden=!near;$('#map-options').hidden=!near;$('#content-page').hidden=near;
    $$('nav a').forEach(a=>{if(a.dataset.page===state.page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    document.title=`${near?'Near me':pageInfo[state.page].title} · Name`;
    if(!near){renderPage();$('#content-page').scrollTop=0;}
  }
  window.addEventListener('hashchange',route);route();
})();
