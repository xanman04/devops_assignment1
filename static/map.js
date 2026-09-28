/* Leaflet 1.9.4; ordinary viewport tile requests, no offline prefetch. */
(() => {
  const element = document.getElementById('map');
  const status = document.getElementById('map-status');
  if (!element || !window.L) {
    if (status) status.textContent = 'The interactive map could not load. Use the event list below.';
    return;
  }
  const form = document.getElementById('map-filters');
  const results = document.getElementById('map-results');
  const localDate = date => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const today = new Date();
  const end = new Date(today); end.setDate(end.getDate()+14);
  form.elements.start.value = localDate(today);
  form.elements.end.value = localDate(end);
  const map = L.map(element).setView([48.8566, 2.3522], 11);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  const markers = L.layerGroup().addTo(map);
  let timer, controller, locationMessage = 'Default area shown. Move the map to explore.';
  function textNode(tag, text) { const node = document.createElement(tag); node.textContent = text; return node; }
  function eventLink(event) { const a = textNode('a', event.title); a.href = `/events/${event.id}/`; return a; }
  function eventTime(event) {
    const options = {dateStyle:'medium', timeStyle:'short', timeZone:event.timezone};
    return `${new Intl.DateTimeFormat(undefined, options).format(new Date(event.starts_at))} (${event.timezone})`;
  }
  async function refresh() {
    if (controller) controller.abort();
    const active = new AbortController(); controller = active;
    status.textContent = 'Finding events in this area…';
    const data = new FormData(form), query = new URLSearchParams();
    try {
      // Browser date controls mean local midnights; send aware ISO instants.
      if (data.get('start')) query.set('start', new Date(`${data.get('start')}T00:00:00`).toISOString());
      if (data.get('end')) query.set('end', new Date(`${data.get('end')}T00:00:00`).toISOString());
      for (const key of ['categories','tags']) if (data.getAll(key).length) query.set(key, data.getAll(key).join(','));
      query.set('match', data.get('match'));
      const bounds = map.getBounds();
      const wrap = value => ((value+180)%360+360)%360-180;
      const wide = bounds.getEast()-bounds.getWest() >= 360;
      query.set('bounds', [Math.max(-90,bounds.getSouth()), wide ? -180 : wrap(bounds.getWest()), Math.min(90,bounds.getNorth()), wide ? 180 : wrap(bounds.getEast())].join(','));
      const response = await fetch(`${element.dataset.endpoint}?${query}`, {signal:active.signal});
      const payload = await response.json();
      if (!response.ok) throw new Error((payload.errors || [payload.error || 'Unable to load events.']).join(' '));
      markers.clearLayers(); results.replaceChildren(textNode('h2','Events in this area'));
      let count = 0;
      for (const venue of payload.venues) {
        const popup = document.createElement('div'); popup.append(textNode('strong', venue.name));
        for (const event of venue.events) {
          count += 1;
          const row = document.createElement('p'); row.append(eventLink(event), textNode('br',''), textNode('span',eventTime(event))); popup.append(row);
          const card = document.createElement('article'); card.className = 'card';
          card.append(eventLink(event), textNode('p',`${venue.name} · ${eventTime(event)}`), textNode('p',event.tags.map(t=>t.name).join(' / ')));
          results.append(card);
        }
        const colors = venue.categories.map(c=>c.color).filter(c=>/^#[0-9a-f]{6}$/i.test(c));
        const dot = textNode('span', venue.count > 1 ? String(venue.count) : ''); dot.className = 'event-pin';
        dot.style.background = colors.length > 1 ? `linear-gradient(135deg,${colors.join(',')})` : colors[0] || '#aaa';
        dot.title = `${venue.name}: ${venue.count} event(s), ${venue.categories.map(c=>c.name).join(', ')}`;
        L.marker([venue.latitude,venue.longitude], {icon:L.divIcon({html:dot,iconSize:[32,32],iconAnchor:[16,16]}), title:dot.title}).bindPopup(popup).addTo(markers);
      }
      if (!count) results.append(textNode('p','No events match this area and date range. Try moving the map or adjusting the filters.'));
      status.textContent = `${count} event(s) at ${payload.venues.length} venue(s). ${locationMessage}`;
    } catch (error) {
      if (error.name !== 'AbortError') status.textContent = error.message;
    }
  }
  const schedule = () => { clearTimeout(timer); timer = setTimeout(refresh,300); };
  map.on('moveend',schedule);
  form.addEventListener('submit', event=>{event.preventDefault(); schedule();});
  form.addEventListener('change',schedule);
  function locate() {
    if (!navigator.geolocation) {locationMessage='Location unavailable; move the map to choose an area.'; schedule(); return;}
    locationMessage='Waiting for location permission…'; schedule();
    navigator.geolocation.getCurrentPosition(position=>{
      locationMessage='Showing your surroundings.';
      map.setView([position.coords.latitude,position.coords.longitude],12); schedule();
    }, ()=>{locationMessage='Location unavailable or declined; move the map to choose an area.'; schedule();}, {timeout:10000,maximumAge:60000});
  }
  document.getElementById('locate').addEventListener('click',locate);
  locate();
})();
