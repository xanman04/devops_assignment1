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
  const map=new MapLibreMap({container:element,style:'https://tiles.openfreemap.org/styles/dark',
    center:[2.3522,48.8566],zoom:11,minZoom:1,attributionControl:true});
  const markers=new Map();
  let locationDot,locationArea=null;
  let timer,controller,selectedVenueId=null,locationMessage='Default area shown. Move the map to explore.';
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
        chip.style.setProperty('--chip-selected-ink',
          channels[0]*0.299+channels[1]*0.587+channels[2]*0.114<130?'#edf0f5':'#262932');
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
      for(const category of event.categories){
        const link=node('a',category.name);link.className='genre';link.href=`/genres/${category.id}/`;
        if(/^#[0-9a-f]{6}$/i.test(category.color)) link.style.setProperty('--genre',category.color);
        tags.append(link);
      }
      for(const tag of event.tags){const label=node('span',tag.name);label.className='tag';tags.append(label);}
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
    status.textContent='Finding events in this area…';
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
      const bounds=map.getBounds(),wrap=value=>((value+180)%360+360)%360-180;
      const wide=bounds.getEast()-bounds.getWest()>=360;
      query.set('bounds',[Math.max(-90,bounds.getSouth()),wide?-180:wrap(bounds.getWest()),Math.min(90,bounds.getNorth()),wide?180:wrap(bounds.getEast())].join(','));
      const response=await fetch(`${element.dataset.endpoint}?${query}`,{signal:active.signal});
      const payload=await response.json();
      if(!response.ok)throw new Error((payload.errors||[payload.error||'Unable to load events.']).join(' '));
      resultItems.replaceChildren();
      let count=0,selected=null;
      const visible=new Set();
      for(const venue of payload.venues){
        visible.add(venue.venue_id);
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
        entry.pin.title=label;
        entry.number.textContent=venue.count>1?String(venue.count):'•';
        if(venue.venue_id===selectedVenueId)selected=venue;
        for(const event of venue.events){
          count+=1;
          const card=node('article','');card.className='card';
          card.append(eventLink(event),node('p',`${venue.name} · ${eventTime(event)}`),node('p',event.tags.map(tag=>tag.name).join(' / ')));
          resultItems.append(card);
        }
      }
      for(const [id,entry] of markers)if(!visible.has(id)){entry.marker.remove();markers.delete(id);}
      if(selected)showVenue(selected);else clearPanel();
      if(!count)resultItems.append(node('p','No events match this area and date range. Move the map or adjust the filters.'));
      status.textContent=`${count} event${count===1?'':'s'} at ${payload.venues.length} venue${payload.venues.length===1?'':'s'}. ${locationMessage}`;
    }catch(error){if(error.name!=='AbortError')status.textContent=error.message;}
  }
  const schedule=()=>{clearTimeout(timer);timer=setTimeout(refresh,300);};
  map.on('moveend',schedule);
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
  function locate(){
    if(!navigator.geolocation){locationMessage='Location unavailable; move the map to choose an area.';schedule();return;}
    locationMessage='Waiting for location permission…';schedule();
    navigator.geolocation.getCurrentPosition(position=>{
      const {latitude,longitude,accuracy}=position.coords;
      const radius=Number.isFinite(accuracy)?Math.max(accuracy,1):1000;
      locationDot?.remove();
      const dot=node('span','');dot.className='location-dot';
      locationDot=new Marker({element:dot}).setLngLat([longitude,latitude]).addTo(map);
      const points=[];
      for(let step=0;step<=64;step++){
        const angle=step*Math.PI/32;
        points.push([longitude+radius*Math.cos(angle)/(111320*Math.cos(latitude*Math.PI/180)),
          latitude+radius*Math.sin(angle)/111320]);
      }
      locationArea={type:'Feature',geometry:{type:'Polygon',coordinates:[points]},properties:{}};
      map.getSource('location-accuracy')?.setData(locationArea);
      const zoom=radius<=75?17:radius<=250?16:radius<=750?15:radius<=2000?13:11;
      locationMessage=`Location estimate within about ${Math.ceil(radius)} m. Move the map to explore.`;
      map.easeTo({center:[longitude,latitude],zoom,duration:650});schedule();
    },()=>{locationMessage='Location unavailable or declined; move the map to choose an area.';schedule();},
    {enableHighAccuracy:true,timeout:15000,maximumAge:0});
  }
  document.getElementById('locate').addEventListener('click',locate);
  map.on('load',()=>{
    map.addSource('location-accuracy',{type:'geojson',data:locationArea||{type:'FeatureCollection',features:[]}});
    map.addLayer({id:'location-accuracy-fill',type:'fill',source:'location-accuracy',
      paint:{'fill-color':'#9bc4eb','fill-opacity':0.1}});
    map.addLayer({id:'location-accuracy-line',type:'line',source:'location-accuracy',
      paint:{'line-color':'#9bc4eb','line-width':1}});
  });
  syncChips();dateLabel();schedule();
  locate();
})();
