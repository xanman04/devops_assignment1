/* Live MapLibre vector map with the OpenFreeMap dark basemap. */
import { Map as MapLibreMap, Marker } from 'maplibre-gl';
(() => {
  const element=document.getElementById('map');
  if (!element) return;
  const status=document.getElementById('map-status');
  const form=document.getElementById('map-filters');
  const results=document.getElementById('map-results');
  const resultItems=document.getElementById('result-items');
  const listToggle=document.getElementById('list-toggle');
  const panel=document.getElementById('event-panel');
  const dateSummary=document.getElementById('date-summary');
  const genreSummary=document.getElementById('genre-summary');
  const categoryInputs=[...form.querySelectorAll('input[name="categories"]')];
  const tagInputs=[...form.querySelectorAll('input[name="tags"]')];
  const genreSearch=document.getElementById('genre-search');
  const subgenreSearch=document.getElementById('subgenre-search');
  const selectAll=document.getElementById('select-all-genres');
  const localDate=date=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const addDays=(date,days)=>{const result=new Date(date);result.setDate(result.getDate()+days);return result;};
  const today=new Date();
  const start=form.elements.start,end=form.elements.end;
  start.value=localDate(today);end.value=localDate(addDays(today,14));
  const cameraKey='bassline-map-camera-v2';
  let savedCamera;
  try{savedCamera=JSON.parse(sessionStorage.getItem(cameraKey));}catch{savedCamera=null;}
  const validCamera=Array.isArray(savedCamera?.center)&&savedCamera.center.length===2&&
    savedCamera.center.every(Number.isFinite)&&Math.abs(savedCamera.center[0])<=180&&
    Math.abs(savedCamera.center[1])<=90&&savedCamera.zoom>=1&&savedCamera.zoom<=20;
  const map=new MapLibreMap({container:element,style:'https://tiles.openfreemap.org/styles/dark',
    center:validCamera?savedCamera.center:[-3.72,40.40],zoom:validCamera?savedCamera.zoom:10.5,
    minZoom:1,attributionControl:true,
    // Keep more nearby zoom levels available when the user reverses a zoom gesture.
    maxTileCacheZoomLevels:8,cancelPendingTileRequestsWhileZooming:false});
  const markers=new Map();
  let locationDot,currentLocation;
  let timer,controller,selectedVenueId=null,lastRefresh=0,lastFilterKey=null;
  const node=(tag,value)=>{const item=document.createElement(tag);item.textContent=value;return item;};
  function eventLink(event) {const link=node('a',event.title);link.href=`/events/${event.id}/`;return link;}
  function eventTime(event) {
    return new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short',timeZone:event.timezone}).format(new Date(event.starts_at));
  }
  function dateLabel() {
    const defaultEnd=localDate(addDays(new Date(),14));
    dateSummary.textContent=start.value===localDate(new Date())&&end.value===defaultEnd?'Next two weeks':
      start.value&&end.value?`${start.value} – ${end.value}`:'Choose dates';
  }
  function genreLabel() {
    const selected=[...categoryInputs,...tagInputs].filter(input=>input.checked).length;
    genreSummary.textContent=selected&&selected!==categoryInputs.length?`${selected} selected`:'All genres';
    selectAll.checked=categoryInputs.length>0&&categoryInputs.every(input=>input.checked);
    selectAll.indeterminate=!selectAll.checked&&categoryInputs.some(input=>input.checked);
  }
  function syncChips() {
    const categories=new Set(categoryInputs.filter(input=>input.checked).map(input=>input.value));
    const genreTerm=genreSearch.value.trim().toLocaleLowerCase();
    const tagTerm=subgenreSearch.value.trim().toLocaleLowerCase();
    for(const chip of document.querySelectorAll('#genre-choices .filter-chip'))
      chip.hidden=!chip.dataset.name.includes(genreTerm);
    for(const chip of document.querySelectorAll('.filter-chip')) {
      const color=getComputedStyle(chip).getPropertyValue('--genre').trim();
      if(/^#[0-9a-f]{6}$/i.test(color)){
        const channels=[1,3,5].map(index=>parseInt(color.slice(index,index+2),16));
        const brightness=channels[0]*0.299+channels[1]*0.587+channels[2]*0.114;
        const lift=brightness<70?0.38:brightness<120?0.2:0;
        chip.style.setProperty('--chip-outline',`rgb(${channels.map(channel=>Math.round(channel+(255-channel)*lift)).join(',')})`);
        chip.style.setProperty('--chip-selected-ink',
          brightness<130?'#edf0f5':'#262932');
      }
    }
    for(const chip of document.querySelectorAll('#subgenre-choices .filter-chip')) {
      const belongs=!categories.size||categories.has(chip.dataset.category);
      if(!belongs)chip.querySelector('input').checked=false;
      chip.hidden=!belongs||!chip.dataset.name.includes(tagTerm);
    }
    genreLabel();
  }
  function showVenue(venue) {
    selectedVenueId=venue.venue_id;
    hideList();
    document.getElementById('panel-venue').textContent=venue.name;
    const rows=document.getElementById('panel-events');rows.replaceChildren();
    for(const event of venue.events){
      const article=document.createElement('article');
      article.append(eventLink(event),node('p',eventTime(event)));
      const tags=document.createElement('div');tags.className='tags';
      const categoryColors=new Map(event.categories.map(category=>[category.id,category.color]));
      for(const category of event.categories){
        const link=node('a',category.name);link.className='genre';link.href=`/genres/${category.id}/`;
        if(/^#[0-9a-f]{6}$/i.test(category.color)) link.style.setProperty('--genre',category.color);
        tags.append(link);
      }
      for(const tag of event.tags){
        const label=node('span',tag.name);label.className='tag';
        const color=categoryColors.get(tag.category_id);
        if(/^#[0-9a-f]{6}$/i.test(color||''))label.style.setProperty('--genre',color);
        tags.append(label);
      }
      article.append(tags);rows.append(article);
    }
    panel.style.borderTopColor=venue.categories[0]?.color || '#9da5b4';
    panel.hidden=false;
  }
  function clearPanel(){panel.hidden=true;selectedVenueId=null;}
  function hideList(){results.hidden=true;listToggle.setAttribute('aria-expanded','false');}
  document.getElementById('panel-close').addEventListener('click',clearPanel);
  document.getElementById('list-close').addEventListener('click',hideList);
  listToggle.addEventListener('click',event=>{
    results.hidden=!results.hidden;
    event.currentTarget.setAttribute('aria-expanded',String(!results.hidden));
    if(!results.hidden)clearPanel();
  });
  element.addEventListener('click',hideList);
  document.addEventListener('keydown',event=>{if(event.key==='Escape')hideList();});
  async function refresh(){
    controller?.abort();const active=new AbortController();controller=active;
    const data=new FormData(form),query=new URLSearchParams();
    try{
      if(data.get('start'))query.set('start',new Date(`${data.get('start')}T00:00:00`).toISOString());
      if(data.get('end'))query.set('end',new Date(`${data.get('end')}T00:00:00`).toISOString());
      const selectedTags=data.getAll('tags');
      const refinedParents=new Set(tagInputs.filter(input=>input.checked)
        .map(input=>input.closest('.filter-chip').dataset.category));
      const broadCategories=data.getAll('categories').filter(id=>!refinedParents.has(id));
      if(broadCategories.length)query.set('categories',broadCategories.join(','));
      if(selectedTags.length)query.set('tags',selectedTags.join(','));
      query.set('match','any');
      const filterKey=query.toString();
      const bounds=map.getBounds(),wrap=value=>((value+180)%360+360)%360-180;
      const south=bounds.getSouth(),north=bounds.getNorth(),west=bounds.getWest(),east=bounds.getEast();
      const longitudeSpan=east-west;
      // At street-level zoom, still preload roughly the neighboring districts.
      const latitudePad=Math.max((north-south)*0.75,0.12);
      const longitudePad=Math.max(longitudeSpan*0.75,0.18);
      const wide=longitudeSpan+2*longitudePad>=360;
      query.set('bounds',[Math.max(-90,south-latitudePad),wide?-180:wrap(west-longitudePad),
        Math.min(90,north+latitudePad),wide?180:wrap(east+longitudePad)].join(','));
      const response=await fetch(`${element.dataset.endpoint}?${query}`,{signal:active.signal});
      const payload=await response.json();
      if(!response.ok)throw new Error((payload.errors||[payload.error||'Unable to load events.']).join(' '));
      resultItems.replaceChildren();
      let count=0,visibleVenueCount=0,selected=null;
      const fetched=new Set();
      for(const venue of payload.venues){
        fetched.add(venue.venue_id);
        const colors=venue.categories.map(c=>c.color).filter(c=>/^#[0-9a-f]{6}$/i.test(c));
        const color=colors.length>1?`linear-gradient(135deg,${colors.join(',')})`:colors[0]||'#a9aab0';
        const label=`${venue.name}: ${venue.count} event${venue.count===1?'':'s'}`;
        let entry=markers.get(venue.venue_id);
        if(!entry){
          const pin=node('button','');pin.type='button';pin.className='event-pin';
          const number=node('span','');pin.append(number);
          entry={pin,number,venue,marker:new Marker({element:pin,anchor:'bottom'})
            .setLngLat([venue.longitude,venue.latitude]).addTo(map)};
          pin.addEventListener('click',()=>showVenue(entry.venue));
          markers.set(venue.venue_id,entry);
        }
        entry.venue=venue;
        entry.marker.setLngLat([venue.longitude,venue.latitude]);
        entry.pin.style.setProperty('--pin-color',color);
        entry.pin.setAttribute('aria-label',label);
        entry.number.textContent=venue.count>1?String(venue.count):'•';
        if(venue.venue_id===selectedVenueId)selected=venue;
        // Keep markers mounted beyond the screen, but report only the visible viewport.
        const longitudeOffset=((venue.longitude-west)%360+360)%360;
        if(venue.latitude<south||venue.latitude>north||longitudeSpan<360&&longitudeOffset>longitudeSpan)continue;
        visibleVenueCount+=1;
        for(const event of venue.events){
          count+=1;
          const card=node('article','');card.className='card';
          const eventColors=event.categories.map(category=>category.color).filter(color=>/^#[0-9a-f]{6}$/i.test(color));
          if(eventColors.length)card.style.setProperty('--event-color',eventColors.length>1?`linear-gradient(180deg,${eventColors.join(',')})`:eventColors[0]);
          card.append(eventLink(event),node('p',`${venue.name} · ${eventTime(event)}`));
          const genres=node('div','');genres.className='tags';
          const categoryColors=new Map(event.categories.map(category=>[category.id,category.color]));
          for(const category of event.categories){
            const genre=node('span',category.name);genre.className='genre';
            if(/^#[0-9a-f]{6}$/i.test(category.color))genre.style.setProperty('--genre',category.color);
            genres.append(genre);
          }
          for(const tag of event.tags){
            const label=node('span',tag.name);label.className='tag';
            const color=categoryColors.get(tag.category_id);
            if(/^#[0-9a-f]{6}$/i.test(color||''))label.style.setProperty('--genre',color);
            genres.append(label);
          }
          card.append(genres);
          resultItems.append(card);
        }
      }
      // Panning can revisit a previously fetched area: retain those markers to avoid a blank interval.
      // A changed date/genre selection invalidates the cache after its replacement data arrives.
      if(filterKey!==lastFilterKey){
        for(const [id,entry] of markers)if(!fetched.has(id)){entry.marker.remove();markers.delete(id);}
      }
      lastFilterKey=filterKey;
      if(selected)showVenue(selected);else clearPanel();
      if(!count)resultItems.append(node('p','No events match this area and date range. Move the map or adjust the filters.'));
      status.textContent=`${count} event${count===1?'':'s'} at ${visibleVenueCount} venue${visibleVenueCount===1?'':'s'}.`;
      lastRefresh=Date.now();
    }catch(error){if(error.name!=='AbortError')status.textContent=error.message;}
  }
  const schedule=()=>{clearTimeout(timer);timer=setTimeout(refresh,300);};
  map.on('moveend',()=>{
    const center=map.getCenter();
    try{sessionStorage.setItem(cameraKey,JSON.stringify({center:[center.lng,center.lat],zoom:map.getZoom()}));}catch{}
    schedule();
  });
  const resumeMap=()=>requestAnimationFrame(()=>{
    map.resize();map.triggerRepaint();
    if(Date.now()-lastRefresh>60000)schedule();
  });
  window.addEventListener('map:shown',resumeMap);
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden&&!element.closest('[hidden]'))resumeMap();
  });
  form.addEventListener('submit',event=>{event.preventDefault();schedule();});
  form.addEventListener('change',event=>{
    if(event.target.name==='categories'||event.target.name==='tags')syncChips();
    dateLabel();genreLabel();schedule();
  });
  selectAll.addEventListener('change',()=>{
    for(const input of categoryInputs)input.checked=selectAll.checked;
    for(const input of tagInputs)input.checked=false;
    syncChips();schedule();
  });
  genreSearch.addEventListener('input',syncChips);
  subgenreSearch.addEventListener('input',syncChips);
  for(const button of document.querySelectorAll('[data-days]'))button.addEventListener('click',()=>{
    const days=Number(button.dataset.days);
    start.value=localDate(new Date());end.value=localDate(addDays(new Date(),days||1));
    dateLabel();document.getElementById('date-menu').open=false;schedule();
  });
  for(const menu of document.querySelectorAll('.filter-menu'))menu.addEventListener('toggle',()=>{
    if(menu.open)document.querySelectorAll('.filter-menu').forEach(other=>{if(other!==menu)other.open=false;});
  });
  document.addEventListener('click',event=>{
    if(!event.target.closest('.filter-menu'))document.querySelectorAll('.filter-menu').forEach(menu=>{menu.open=false;});
  });
  function moveToLocation(latitude,longitude,zoom){
    map.flyTo({center:[longitude,latitude],zoom,duration:1400,curve:1.2,essential:true});
  }
  function locate(recenter=true){
    if(currentLocation){moveToLocation(currentLocation.latitude,currentLocation.longitude,currentLocation.zoom);return;}
    if(!navigator.geolocation)return;
    navigator.geolocation.getCurrentPosition(position=>{
      const {latitude,longitude,accuracy}=position.coords;
      const radius=Number.isFinite(accuracy)?Math.max(accuracy,1):1000;
      locationDot?.remove();
      const dot=node('span','');dot.className='location-dot';
      locationDot=new Marker({element:dot}).setLngLat([longitude,latitude]).addTo(map);
      const zoom=radius<=75?17:radius<=250?16:radius<=750?15:radius<=2000?13:11;
      currentLocation={latitude,longitude,zoom};
      if(recenter||!validCamera)moveToLocation(latitude,longitude,zoom);
    },()=>{},
    {enableHighAccuracy:true,timeout:15000,maximumAge:0});
  }
  document.getElementById('locate').addEventListener('click',()=>locate(true));
  map.on('style.load',()=>{
    const palette={
      background:{'background-color':'#252b32'},
      water:{'fill-color':'#20323b'},waterway:{'line-color':'#30444e'},
      landuse_residential:{'fill-color':'#2b3037'},landuse_park:{'fill-color':'#2d3c35'},
      landcover_wood:{'fill-color':'#2b3932'},
      building:{'fill-color':'#333941','fill-outline-color':'#444c55'},
      highway_path:{'line-color':'#48515a'},highway_minor:{'line-color':'#505a64'},
      highway_major_casing:{'line-color':'#39414a'},highway_major_inner:{'line-color':'#65707b'},
      highway_major_subtle:{'line-color':'#48525c'},
      highway_motorway_casing:{'line-color':'#3e4852'},highway_motorway_inner:{'line-color':'#737e89'},
      railway:{'line-color':'#4a545e'},railway_minor:{'line-color':'#424c56'},
      highway_name_other:{'text-color':'#a9b1ba','text-halo-color':'#252b32'},
      highway_name_motorway:{'text-color':'#b5bdc5'},
    };
    for(const [id,paint] of Object.entries(palette)){
      if(!map.getLayer(id))continue;
      for(const [property,color] of Object.entries(paint))map.setPaintProperty(id,property,color);
    }
    if(map.getLayer('landcover_wood'))map.setPaintProperty('landcover_wood','fill-pattern',null);
    if(map.getLayer('highway_minor'))map.setLayerZoomRange('highway_minor',12,24);
    if(map.getLayer('highway_path'))map.setLayerZoomRange('highway_path',13,24);
    for(const layer of map.getStyle().layers){
      if(layer.id.startsWith('place_')&&layer.type==='symbol'){
        map.setPaintProperty(layer.id,'text-color','#c1c8cf');
        map.setPaintProperty(layer.id,'text-halo-color','#252b32');
      }
    }
  });
  syncChips();dateLabel();schedule();
  locate(false);
})();
