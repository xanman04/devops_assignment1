// Copyright © 2026 Xander Chen. All rights reserved.
/* Notice when this browser's login changes in another tab, and stop this tab from showing the old account. */
(() => {
  const mine = document.body.dataset.account || '';
  const root = document.body.dataset.root || '/';
  let shown = false, checking = false;

  function block(now) {
    if (shown) return;
    shown = true;
    const overlay = document.createElement('div');
    overlay.className = 'account-changed';
    overlay.setAttribute('role', 'alertdialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'account-changed-title');
    const panel = document.createElement('div');
    panel.className = 'account-changed-panel';
    const title = document.createElement('h2');
    title.id = 'account-changed-title';
    title.textContent = now.id ? 'Your account changed in another tab' : 'You were signed out in another tab';
    const text = document.createElement('p');
    text.textContent = now.id
      ? `This browser is now signed in as ${now.name}. This tab still shows the previous account, so reload it to continue.`
      : 'Sign in again to continue.';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-primary';
    button.textContent = now.id ? 'Reload this tab' : 'Go to log in';
    button.addEventListener('click', () => { if (now.id) location.reload(); else location.assign(root + 'accounts/login/'); });
    panel.append(title, text, button);
    overlay.append(panel);
    document.body.append(overlay);
    document.body.classList.add('account-locked');
    button.focus();
  }

  async function check() {
    if (shown || checking) return;
    checking = true;
    try {
      const response = await fetch(root + 'accounts/whoami/', { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } });
      if (!response.ok) return;
      const now = await response.json();
      if ((now.id == null ? '' : String(now.id)) !== mine) block(now);
    } catch { /* offline: try again later */ }
    finally { checking = false; }
  }

  // Signing in from an address without a tab prefix moves this tab to its own slot first, so the new login
  // cannot replace the account shown in other tabs.
  document.addEventListener('submit', event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.hasAttribute('data-new-session') || root !== '/') return;
    try {
      let slot = sessionStorage.getItem('bassline-slot');
      if (!/^t[0-9a-f]{8}$/.test(slot || '')) {
        const bytes = crypto.getRandomValues(new Uint8Array(4));
        slot = 't' + Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
      }
      sessionStorage.setItem('bassline-slot', slot);
      form.action = '/' + slot + location.pathname + location.search;
      const next = form.querySelector('input[name=next]');
      if (next && next.value.startsWith('/') && !next.value.startsWith('//')) next.value = '/' + slot + next.value;
    } catch { /* no storage: sign in the ordinary way */ }
  }, true);

  document.addEventListener('visibilitychange', () => { if (!document.hidden) check(); });
  window.addEventListener('focus', check);
  setInterval(() => { if (!document.hidden) check(); }, 15000);
})();
