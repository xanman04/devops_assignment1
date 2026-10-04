// Copyright © 2026 Xander Chen. All rights reserved.
/* Keep the live map mounted while moving among the app's main pages. */
(() => {
  const main=document.getElementById('main-content');
  const mapPage=main?.querySelector('.live-map-page');
  const filters=document.getElementById('map-filters');
  if(!mapPage||!filters)return;

  const root=document.body.dataset.root||'/';
  const local=path=>path.startsWith(root)?'/'+path.slice(root.length):path;
  const routes=new Set(['/','/discover/','/my-events/','/groups/','/notifications/','/accounts/settings/','/accounts/profile/']);
  let controller;

  function updateNav(path){
    for(const link of document.querySelectorAll('.live-nav a')){
      if(local(new URL(link.href).pathname)===local(path))link.setAttribute('aria-current','page');
      else link.removeAttribute('aria-current');
    }
  }

  function showMap(url,push){
    controller?.abort();
    window.cleanupBrowse?.();
    for(const child of [...main.childNodes])if(child!==mapPage)child.remove();
    document.body.className='home-layout';
    mapPage.hidden=false;
    filters.hidden=false;
    document.title='Bassline';
    document.getElementById('site-search').value='';
    updateNav(root);
    if(push)history.pushState({},'',url);
    requestAnimationFrame(()=>window.dispatchEvent(new Event('map:shown')));
  }

  async function navigate(url,push=true){
    const target=new URL(url,location.href);
    if(target.origin!==location.origin||!routes.has(local(target.pathname))){
      location.assign(target.href);return;
    }
    if(local(target.pathname)==='/'){showMap(target.href,push);return;}
    controller?.abort();
    const active=new AbortController();controller=active;
    try{
      const response=await fetch(target.href,{signal:active.signal,credentials:'same-origin'});
      if(!response.ok||new URL(response.url).pathname!==target.pathname)throw new Error('Navigation unavailable');
      const page=new DOMParser().parseFromString(await response.text(),'text/html');
      const content=page.getElementById('main-content');
      if(!content)throw new Error('Page content unavailable');
      // The login changed in another tab: never mix accounts, load the page normally instead.
      if((page.body.dataset.account||'')!==(document.body.dataset.account||''))throw new Error('Account changed');
      window.cleanupBrowse?.();
      for(const child of [...main.childNodes])if(child!==mapPage)child.remove();
      main.append(...[...content.childNodes]);
      mapPage.hidden=true;
      filters.hidden=true;
      for(const menu of filters.querySelectorAll('details'))menu.open=false;
      document.body.className=page.body.className;
      document.title=page.title;
      document.getElementById('site-search').value=target.searchParams.get('q')||'';
      updateNav(target.pathname);
      main.scrollTop=0;
      window.initializeBrowse?.();
      window.initializeCrop?.();
      if(push)history.pushState({},'',target.href);
    }catch(error){
      if(error.name!=='AbortError')location.assign(target.href);
    }
  }

  document.addEventListener('click',event=>{
    const link=event.target.closest('a[href]');
    if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.target||link.hasAttribute('download'))return;
    const target=new URL(link.href,location.href);
    if(target.origin!==location.origin||!routes.has(local(target.pathname)))return;
    event.preventDefault();navigate(target.href);
  });
  document.querySelector('.live-search').addEventListener('submit',event=>{
    event.preventDefault();
    const query=new FormData(event.currentTarget).get('q').trim();
    navigate(`${root}discover/${query?`?q=${encodeURIComponent(query)}`:''}`);
  });
  window.addEventListener('popstate',()=>navigate(location.href,false));
})();
