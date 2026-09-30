/* Live Leaflet map with an OpenFreeMap vector basemap. */
import * as L from 'leaflet';
import { maplibreGL } from 'https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/dist/leaflet-maplibre-gl.mjs';
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
  const localDate=date=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const addDays=(date,days)=>{const result=new Date(date);result.setDate(result.getDate()+days);return result;};
  const today=new Date();
  const start=form.elements.start,end=form.elements.end;
  start.value=localDate(today);end.value=localDate(addDays(today,14));
  const map=L.map(element,{zoomControl:false,minZoom:1}).setView([48.8566,2.3522],11);
  maplibreGL({style:'https://tiles.openfreemap.org/styles/dark'}).addTo(map);
  const markers=L.layerGroup().addTo(map);
  let locationCircle,locationDot;
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
    const selected=form.querySelectorAll('input[name="categories"]:checked,input[name="tags"]:checked');
    genreSummary.textContent=selected.length?`${selected.length} selected`:'All genres';
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
      for(const key of ['categories','tags'])if(data.getAll(key).length)query.set(key,data.getAll(key).join(','));
      query.set('match',data.get('match'));
      const bounds=map.getBounds(),wrap=value=>((value+180)%360+360)%360-180;
      const wide=bounds.getEast()-bounds.getWest()>=360;
      query.set('bounds',[Math.max(-90,bounds.getSouth()),wide?-180:wrap(bounds.getWest()),Math.min(90,bounds.getNorth()),wide?180:wrap(bounds.getEast())].join(','));
      const response=await fetch(`${element.dataset.endpoint}?${query}`,{signal:active.signal});
      const payload=await response.json();
      if(!response.ok)throw new Error((payload.errors||[payload.error||'Unable to load events.']).join(' '));
      markers.clearLayers();resultItems.replaceChildren();
      let count=0,selected=null;
      for(const venue of payload.venues){
        const colors=venue.categories.map(c=>c.color).filter(c=>/^#[0-9a-f]{6}$/i.test(c));
        const color=colors.length>1?`linear-gradient(135deg,${colors.join(',')})`:colors[0]||'#a9aab0';
        const dot=node('span','');dot.className='event-pin';dot.style.setProperty('--pin-color',color);
        const number=node('span',venue.count>1?String(venue.count):'•');dot.append(number);
        const label=`${venue.name}: ${venue.count} event${venue.count===1?'':'s'}`;
        const marker=L.marker([venue.latitude,venue.longitude],{
          icon:L.divIcon({html:dot,iconSize:[46,58],iconAnchor:[23,55]}),title:label,alt:label,keyboard:true,
        }).addTo(markers);
        marker.on('click',()=>showVenue(venue));
        if(venue.venue_id===selectedVenueId)selected=venue;
        for(const event of venue.events){
          count+=1;
          const card=node('article','');card.className='card';
          card.append(eventLink(event),node('p',`${venue.name} · ${eventTime(event)}`),node('p',event.tags.map(tag=>tag.name).join(' / ')));
          resultItems.append(card);
        }
      }
      if(selected)showVenue(selected);else clearPanel();
      if(!count)resultItems.append(node('p','No events match this area and date range. Move the map or adjust the filters.'));
      status.textContent=`${count} event${count===1?'':'s'} at ${payload.venues.length} venue${payload.venues.length===1?'':'s'}. ${locationMessage}`;
    }catch(error){if(error.name!=='AbortError')status.textContent=error.message;}
  }
  const schedule=()=>{clearTimeout(timer);timer=setTimeout(refresh,300);};
  map.on('moveend',schedule);
  form.addEventListener('submit',event=>{event.preventDefault();schedule();});
  form.addEventListener('change',()=>{dateLabel();genreLabel();schedule();});
  for(const button of document.querySelectorAll('[data-days]'))button.addEventListener('click',()=>{
    const days=Number(button.dataset.days);
    start.value=localDate(new Date());end.value=localDate(addDays(new Date(),days||1));
    dateLabel();document.getElementById('date-menu').open=false;schedule();
  });
  document.getElementById('clear-genres').addEventListener('click',()=>{
    form.querySelectorAll('input[name="categories"],input[name="tags"]').forEach(input=>{input.checked=false;});
    genreLabel();schedule();
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
      locationCircle?.remove();locationDot?.remove();
      locationCircle=L.circle([latitude,longitude],{radius,color:'#9bc4eb',weight:1,fillColor:'#9bc4eb',fillOpacity:.1,interactive:false}).addTo(map);
      locationDot=L.circleMarker([latitude,longitude],{radius:5,color:'#fff',weight:2,fillColor:'#69aeed',fillOpacity:1,interactive:false}).addTo(map);
      const zoom=radius<=75?17:radius<=250?16:radius<=750?15:radius<=2000?13:11;
      locationMessage=`Location estimate within about ${Math.ceil(radius)} m. Move the map to explore.`;
      map.setView([latitude,longitude],zoom);schedule();
    },()=>{locationMessage='Location unavailable or declined; move the map to choose an area.';schedule();},
    {enableHighAccuracy:true,timeout:15000,maximumAge:0});
  }
  document.getElementById('locate').addEventListener('click',locate);
  locate();
})();
