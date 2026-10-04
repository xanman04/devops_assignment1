// Copyright © 2026 Xander Chen. All rights reserved.
/* Collection: genre chips filter the badges, and clicking a badge opens it large over the board.
   The open card follows the pointer in 3D and its foil changes colour with the angle, a bit like a collectible card
   game. Everything is delegated from the document, so it also works on pages swapped in without a reload. */
(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let view = null, card = null, opener = null, frame = 0;
  const pose = { x: 0, y: 0, tx: 0, ty: 0 };      // x, y: where the card is now; tx, ty: where the pointer wants it (-1 to 1)

  /* ---------- genre chips ---------- */
  function filterBoard(board, genre) {
    const list = board.querySelector('.badge-board');
    if (!list) return;
    let shown = 0;
    for (const item of list.children) {
      if (item.classList.contains('badge-empty')) continue;
      const match = !genre || item.dataset.genre === genre;
      item.hidden = !match;
      if (match) shown += 1;
    }
    const empty = list.querySelector('.badge-empty');
    if (empty) empty.hidden = shown > 0;
    for (const chip of board.querySelectorAll('.gchart-chip[data-genre]')) {
      chip.setAttribute('aria-pressed', String((chip.dataset.genre || '') === (genre || '')));
    }
    list.scrollTop = 0;
  }

  /* ---------- the open badge ---------- */
  function paint() {
    pose.x += (pose.tx - pose.x) * 0.14;
    pose.y += (pose.ty - pose.y) * 0.14;
    if (card) {
      card.style.setProperty('--px', pose.x.toFixed(4));
      card.style.setProperty('--py', pose.y.toFixed(4));
      card.style.transform = `translate3d(${(pose.x * 34).toFixed(1)}px, ${(pose.y * 34).toFixed(1)}px, 0) rotateX(${(-pose.y * 22).toFixed(2)}deg) rotateY(${(pose.x * 26).toFixed(2)}deg)`;
      // The light stays where it is; turning the card moves the shine across its surface.
      card.style.setProperty('--lx', (-pose.x).toFixed(4));
      card.style.setProperty('--ly', (-pose.y).toFixed(4));
      card.style.setProperty('--tilt', Math.min(1, Math.hypot(pose.x, pose.y)).toFixed(4));
    }
    const settled = reduce || (Math.abs(pose.tx - pose.x) < 0.001 && Math.abs(pose.ty - pose.y) < 0.001);
    frame = settled ? 0 : requestAnimationFrame(paint);
  }

  function aim(event) {
    if (!view) return;
    const box = view.getBoundingClientRect();
    pose.tx = Math.max(-1, Math.min(1, ((event.clientX - box.left) / box.width - 0.5) * 2));
    pose.ty = Math.max(-1, Math.min(1, ((event.clientY - box.top) / box.height - 0.5) * 2));
    if (reduce) { pose.x = pose.tx; pose.y = pose.ty; paint(); return; }   // follows the pointer directly, no easing
    if (!frame) frame = requestAnimationFrame(paint);
  }

  function close() {
    if (!view) return;
    cancelAnimationFrame(frame);
    frame = 0;
    view.remove();
    view = card = null;
    if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
    opener = null;
  }

  function open(tile) {
    const board = tile.closest('.profile-board');
    if (!board) return;
    close();
    opener = tile;
    const title = tile.querySelector('strong')?.textContent || 'Badge';
    const detail = tile.querySelector('small')?.textContent || '';
    view = document.createElement('div');
    view.className = 'badge-view';
    view.setAttribute('role', 'dialog');
    view.setAttribute('aria-modal', 'true');
    view.setAttribute('aria-label', title);
    const stage = document.createElement('div');
    stage.className = 'badge-stage';
    card = document.createElement('div');
    const achievement = tile.classList.contains('badge-card--achievement');
    card.className = 'badge-big badge-big--' + (achievement ? 'achievement' : 'event');
    if (tile.dataset.tier) card.classList.add('tier-' + tile.dataset.tier.toLowerCase());
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', title + '. Press to turn the card over.');
    const look = getComputedStyle(tile);
    for (const name of ['--badge', '--f1', '--f2', '--f3']) card.style.setProperty(name, look.getPropertyValue(name));

    const flip = document.createElement('div');
    flip.className = 'badge-flip';
    const front = document.createElement('div');
    front.className = 'badge-face badge-front';
    const art = tile.querySelector('.badge-art');
    if (art) front.append(art.cloneNode(true));
    const foil = document.createElement('div');
    foil.className = 'badge-big-foil';
    foil.setAttribute('aria-hidden', 'true');
    for (const name of ['sheen', 'lines', 'sparkle', 'glare']) {
      const layer = document.createElement('i');
      layer.className = 'foil-' + name;
      foil.append(layer);
    }
    front.append(foil);

    const back = document.createElement('div');
    back.className = 'badge-face badge-back';
    const kicker = document.createElement('p');
    kicker.className = 'badge-back-kicker';
    kicker.textContent = achievement ? (tile.dataset.tier || '') + ' achievement' : 'Event card';
    const heading = document.createElement('h3');
    heading.textContent = title;
    const sub = document.createElement('p');
    sub.className = 'badge-back-detail';
    sub.textContent = detail + (tile.dataset.genre ? ' · ' + tile.dataset.genre : '');
    back.append(kicker, heading, sub);
    const proof = tile.querySelector('.badge-proof');
    if (proof) {
      back.append(proof.cloneNode(true));
    } else {
      const note = document.createElement('p');
      note.className = 'badge-back-note';
      note.textContent = 'Attendance verified at the venue.';
      back.append(note);
    }
    flip.append(front, back);
    card.append(flip);
    stage.append(card);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'badge-view-close';
    button.textContent = 'Close';
    const hint = document.createElement('p');
    hint.className = 'badge-view-hint';
    hint.textContent = 'Click the card to turn it over. Click anywhere else to close.';
    view.append(stage, button, hint);
    board.append(view);
    view.addEventListener('pointerleave', () => {
      pose.tx = pose.ty = 0;
      if (reduce) { pose.x = pose.y = 0; paint(); } else if (!frame) frame = requestAnimationFrame(paint);
    });
    pose.x = pose.y = pose.tx = pose.ty = 0;
    paint();
    card.focus({ preventScroll: true });
  }

  function turn() { if (card) card.classList.toggle('is-flipped'); }

  document.addEventListener('click', event => {
    const chip = event.target.closest && event.target.closest('.gchart-chip[data-genre]');
    if (chip) {
      const board = chip.closest('.profile-board');
      const wanted = chip.dataset.genre;
      filterBoard(board, chip.getAttribute('aria-pressed') === 'true' ? '' : wanted);
      return;
    }
    if (view) {
      if (event.target.closest('.badge-view-close')) { close(); return; }
      if (event.target.closest('.badge-big')) turn(); else close();
      return;
    }
    const tile = event.target.closest && event.target.closest('.badge-card');
    if (tile && !view) open(tile);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && view) { event.preventDefault(); close(); return; }
    if ((event.key === 'Enter' || event.key === ' ') && view && event.target.closest && event.target.closest('.badge-big')) { event.preventDefault(); turn(); return; }
    if ((event.key === 'Enter' || event.key === ' ') && !view) {
      const tile = event.target.closest && event.target.closest('.badge-card');
      if (tile) { event.preventDefault(); open(tile); }
    }
  });
  document.addEventListener('pointermove', event => { if (view && view.contains(event.target)) aim(event); });
})();
