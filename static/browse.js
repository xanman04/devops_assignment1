window.initializeBrowse = () => {
  window.cleanupBrowse?.();
  const observers=[];
  const controller=new AbortController();
  for (const row of document.querySelectorAll('.browse-track')) {
    const id=row.id.slice(4);
    const previous=document.querySelector(`[data-row="${id}"][data-direction="-1"]`);
    const next=document.querySelector(`[data-row="${id}"][data-direction="1"]`);
    if (!previous || !next) continue;
    const update=()=>{
      previous.disabled=row.scrollLeft<=1;
      next.disabled=row.scrollLeft+row.clientWidth>=row.scrollWidth-1;
    };
    for (const button of [previous,next]) button.addEventListener('click',()=>{
      row.scrollBy({left:Number(button.dataset.direction)*row.clientWidth*.8,
                    behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
    });
    row.addEventListener('scroll',update);
    const observer=new ResizeObserver(update);observer.observe(row);observers.push(observer);
    update();
  }
  window.cleanupBrowse=()=>{controller.abort();observers.forEach(observer=>observer.disconnect());};
  const playing=document.querySelector('[data-playing-endpoint]');
  if (playing) {
    const track=playing.querySelector('.browse-track');
    const searchQuery=playing.dataset.searchQuery;
    const showMessage=message=>{
      if(searchQuery){playing.remove();const empty=document.querySelector('.discover-no-results');if(empty&&!document.querySelector('.browse-row')){empty.hidden=false;document.querySelector('.search-heading')?.remove();}return;}
      track.replaceChildren();const placeholder=document.createElement('p');placeholder.className='browse-empty';placeholder.textContent=message;track.append(placeholder);track.dispatchEvent(new Event('scroll'));
    };
    const showCards=cards=>{
      track.replaceChildren();
      if (!cards.length){showMessage('No linked artists or DJs are playing within 30 km in the next two weeks.');return;}
      for (const card of cards) {
        const link=document.createElement('a');link.className='browse-tile artist-tile';link.href=card.href;
        if(card.categories.length)link.style.setProperty('--tile-color',card.categories[0].color);
        const art=document.createElement('span');art.className='browse-art'+(card.photo_url?' dj-browse-photo':'');
        if(card.photo_url){const photo=document.createElement('img');photo.src=card.photo_url;photo.alt='';photo.loading='lazy';art.append(photo);}
        else {const icon=document.createElementNS('http://www.w3.org/2000/svg','svg');icon.classList.add('live-icon');const use=document.createElementNS('http://www.w3.org/2000/svg','use');use.setAttribute('href','#icon-profile');icon.append(use);art.append(icon);}
        const title=document.createElement('strong');title.textContent=card.title;
        const subtitle=document.createElement('small');subtitle.textContent=card.subtitle;
        link.append(art,title,subtitle);
        if(card.categories.length){const chips=document.createElement('span');chips.className='browse-dj-chips';
          for(const category of card.categories){const chip=document.createElement('span');chip.className='genre';chip.style.setProperty('--genre',category.color);chip.textContent=category.name;chips.append(chip);}link.append(chips);}
        track.append(link);
      }
      track.dispatchEvent(new Event('scroll'));
    };
    if (!navigator.geolocation) showMessage('Enable location access to see performers playing near you.');
    else navigator.geolocation.getCurrentPosition(async position=>{
      if(controller.signal.aborted||!playing.isConnected)return;
      const url=new URL(playing.dataset.playingEndpoint,location.origin);
      url.searchParams.set('latitude',position.coords.latitude);
      url.searchParams.set('longitude',position.coords.longitude);
      if(playing.dataset.searchQuery)url.searchParams.set('q',playing.dataset.searchQuery);
      try{const response=await fetch(url,{signal:controller.signal,credentials:'same-origin'});
        if(!response.ok)throw new Error('Nearby performers unavailable');
        const data=await response.json();if(!controller.signal.aborted&&playing.isConnected)showCards(data.cards);
      }catch(error){if(error.name!=='AbortError'&&playing.isConnected)showMessage('Could not load nearby performers. Try Discover again.');}
    },()=>{if(playing.isConnected)showMessage('Enable location access to see performers playing near you.');},
    {enableHighAccuracy:false,maximumAge:300000,timeout:8000});
  }
};
window.initializeBrowse();

const linkedSubgenre=location.hash.startsWith('#subgenre-')?document.getElementById(location.hash.slice(1)):null;
if(linkedSubgenre?.matches('.subgenre-card'))linkedSubgenre.open=true;

// Keep one subgenre expanded at a time and dismiss it when attention moves away.
document.addEventListener('click', event => {
  const card = event.target instanceof Element ? event.target.closest('.subgenre-card') : null;
  for (const openCard of document.querySelectorAll('.subgenre-card[open]')) {
    if (openCard !== card) openCard.open = false;
  }
}, true);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    for (const card of document.querySelectorAll('.subgenre-card[open]')) card.open = false;
  }
});
document.addEventListener('click', event => {
  const link=event.target instanceof Element ? event.target.closest('[data-back-link]') : null;
  if (!link || event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  if (document.referrer && new URL(document.referrer).origin===location.origin && history.length>1) {
    event.preventDefault();history.back();
  }
});
