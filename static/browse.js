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
