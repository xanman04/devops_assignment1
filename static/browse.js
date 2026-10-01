window.initializeBrowse = () => {
  window.cleanupBrowse?.();
  const observers=[];
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
  window.cleanupBrowse=()=>observers.forEach(observer=>observer.disconnect());
};
window.initializeBrowse();

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
