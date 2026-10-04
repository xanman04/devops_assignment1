// Copyright © 2026 Xander Chen. All rights reserved.
/* Joining a group while already in another group for the same event asks first, in a popup. */
(() => {
  function ask(name) {
    return new Promise(resolve => {
      const overlay = document.createElement('div');
      overlay.className = 'cropper';
      overlay.setAttribute('role', 'alertdialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-labelledby', 'switch-title');
      const panel = document.createElement('div');
      panel.className = 'cropper-panel';
      const title = document.createElement('h2');
      title.id = 'switch-title';
      title.textContent = 'Leave your current group?';
      const text = document.createElement('p');
      text.className = 'cropper-hint';
      text.textContent = 'To join this group you must leave "' + name + '", your current group for this event. Do you want to continue?';
      text.style.fontSize = '0.9375rem';
      const actions = document.createElement('div');
      actions.className = 'cropper-actions';
      const no = document.createElement('button');
      no.type = 'button';
      no.className = 'cropper-cancel';
      no.textContent = 'Stay in my group';
      const yes = document.createElement('button');
      yes.type = 'button';
      yes.className = 'cropper-use';
      yes.textContent = 'Leave and join';
      actions.append(no, yes);
      panel.append(title, text, actions);
      overlay.append(panel);
      const done = answer => { overlay.remove(); document.removeEventListener('keydown', onKey, true); resolve(answer); };
      const onKey = event => { if (event.key === 'Escape') { event.preventDefault(); done(false); } };
      no.addEventListener('click', () => done(false));
      yes.addEventListener('click', () => done(true));
      overlay.addEventListener('pointerdown', event => { if (event.target === overlay) done(false); });
      document.addEventListener('keydown', onKey, true);
      document.body.append(overlay);
      no.focus();
    });
  }

  document.addEventListener('submit', async event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.switchFrom || form.dataset.confirmed) return;
    event.preventDefault();
    if (await ask(form.dataset.switchFrom)) {
      form.dataset.confirmed = '1';
      const flag = form.querySelector('[data-switch-flag]');
      if (flag) flag.value = 'on';
      form.submit();
    }
  });
})();
