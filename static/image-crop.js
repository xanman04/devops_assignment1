/* Picture adjuster. Choosing a picture opens a popup showing it under an overlay the size of the frame it will be
   shown in (a circle for profile pictures). Drag to move it, pinch, scroll or use the slider to zoom, then "Use photo".
   The visible part is cut out in the browser and replaces the file in the form, so the server only receives what is
   shown. Without JavaScript the original file is sent unchanged. */
(() => {
  const OUTPUT = 1200;           // long side of the saved picture, in pixels
  const MAX_ZOOM = 5;

  /* Where the picture goes in a W x H frame: never smaller than the frame, never leaving a gap. */
  function layout(nw, nh, W, H, zoom, x, y) {
    const scale = Math.max(W / nw, H / nh) * Math.min(Math.max(zoom, 1), MAX_ZOOM);
    const width = nw * scale, height = nh * scale;
    return { scale, width, height,
      x: Math.min(0, Math.max(W - width, x)),
      y: Math.min(0, Math.max(H - height, y)) };
  }

  /* Change zoom but keep whatever is at the middle of the frame in the middle. */
  function zoomAround(nw, nh, W, H, current, zoom) {
    const centreX = (W / 2 - current.x) / current.scale, centreY = (H / 2 - current.y) / current.scale;
    const base = Math.max(W / nw, H / nh) * Math.min(Math.max(zoom, 1), MAX_ZOOM);
    return layout(nw, nh, W, H, zoom, W / 2 - centreX * base, H / 2 - centreY * base);
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function setup(input) {
    if (input.dataset.cropReady) return;
    input.dataset.cropReady = '1';
    const ratio = Number(input.dataset.cropAspect) || 1;
    const circle = input.dataset.cropShape === 'circle';

    const chip = el('div', 'crop-chip');
    chip.hidden = true;
    const thumb = el('img', circle ? 'is-circle' : '');
    thumb.alt = '';
    const label = el('span', '', 'Picture ready. It will look like this.');
    const again = el('button', '', 'Adjust');
    again.type = 'button';
    chip.append(thumb, label, again);
    input.insertAdjacentElement('afterend', chip);
    const currentSrc = input.dataset.currentSrc || '';
    if (currentSrc) {
      thumb.src = currentSrc;
      label.textContent = 'Your current picture. Adjust it, or choose a new file above.';
      chip.hidden = false;
    }

    let source = null, thumbUrl = '';

    function edit(file, isNew) {
      const url = URL.createObjectURL(file);
      const modal = el('div', 'cropper');
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      modal.setAttribute('aria-label', 'Adjust your picture');
      const panel = el('div', 'cropper-panel');
      const stage = el('div', 'cropper-stage');
      stage.tabIndex = 0;
      stage.setAttribute('aria-label', 'Picture. Drag, or use the arrow keys, to move it. Plus and minus zoom.');
      const frame = el('div', 'cropper-frame' + (circle ? ' is-circle' : '') + (ratio > 1.2 ? ' is-wide' : ''));
      frame.style.aspectRatio = String(ratio);
      const image = el('img');
      image.alt = '';
      image.draggable = false;
      const mask = el('div', 'cropper-mask');
      frame.append(image, mask);
      stage.append(frame);
      const zoomRow = el('label', 'cropper-zoom', 'Zoom');
      const zoom = el('input');
      zoom.type = 'range';
      zoom.min = '1';
      zoom.max = String(MAX_ZOOM);
      zoom.step = '0.01';
      zoom.value = '1';
      zoomRow.append(zoom);
      const hint = el('p', 'cropper-hint', 'Drag the picture, or pinch to zoom, until it sits the way you want inside the outline.');
      const actions = el('div', 'cropper-actions');
      const cancel = el('button', 'cropper-cancel', 'Cancel');
      cancel.type = 'button';
      const use = el('button', 'cropper-use', 'Use photo');
      use.type = 'button';
      actions.append(cancel, use);
      panel.append(el('h2', '', 'Adjust your picture'), stage, zoomRow, hint, actions);
      modal.append(panel);

      let state = null, zoomValue = 1, drag = null, pinch = null;
      const pointers = new Map();
      const size = () => ({ W: frame.clientWidth, H: frame.clientHeight });
      const paint = () => {
        image.style.width = state.width + 'px';
        image.style.height = state.height + 'px';
        image.style.left = state.x + 'px';
        image.style.top = state.y + 'px';
      };
      const setZoom = value => {
        zoomValue = Math.min(MAX_ZOOM, Math.max(1, value));
        zoom.value = String(zoomValue);
        const { W, H } = size();
        state = zoomAround(image.naturalWidth, image.naturalHeight, W, H, state, zoomValue);
        paint();
      };
      const move = (dx, dy) => {
        const { W, H } = size();
        state = layout(image.naturalWidth, image.naturalHeight, W, H, zoomValue, state.x + dx, state.y + dy);
        paint();
      };

      function close(keepFocus) {
        modal.remove();
        URL.revokeObjectURL(url);
        document.removeEventListener('keydown', onKey, true);
        document.body.classList.remove('crop-open');
        if (keepFocus) input.focus({ preventScroll: true });
      }

      function discard() {
        close(true);
        if (isNew) { input.value = ''; chip.hidden = true; source = null; }
      }

      function accept() {
        const { W } = size();
        const outW = ratio >= 1 ? OUTPUT : Math.round(OUTPUT * ratio), outH = Math.round(outW / ratio), k = outW / W;
        const canvas = document.createElement('canvas');
        canvas.width = outW;
        canvas.height = outH;
        const context = canvas.getContext('2d');
        context.fillStyle = '#fff';
        context.fillRect(0, 0, outW, outH);
        context.drawImage(image, state.x * k, state.y * k, state.width * k, state.height * k);
        canvas.toBlob(blob => {
          if (!blob) { close(true); return; }
          const transfer = new DataTransfer();
          transfer.items.add(new File([blob], 'picture.jpg', { type: 'image/jpeg' }));
          input.files = transfer.files;          // assigning files does not fire another change event
          source = file;
          if (thumbUrl) URL.revokeObjectURL(thumbUrl);
          thumbUrl = URL.createObjectURL(blob);
          thumb.src = thumbUrl;
          chip.hidden = false;
          close(true);
        }, 'image/jpeg', 0.9);
      }

      function onKey(event) {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); discard(); return; }
        if (event.target !== stage || !state) return;
        const step = { ArrowLeft: [10, 0], ArrowRight: [-10, 0], ArrowUp: [0, 10], ArrowDown: [0, -10] }[event.key];
        if (step) { event.preventDefault(); move(step[0], step[1]); return; }
        if (event.key === '+' || event.key === '=') { event.preventDefault(); setZoom(zoomValue + 0.2); }
        if (event.key === '-') { event.preventDefault(); setZoom(zoomValue - 0.2); }
      }

      const spread = () => { const [a, b] = [...pointers.values()]; return Math.hypot(a.x - b.x, a.y - b.y) || 1; };
      stage.addEventListener('pointerdown', event => {
        if (!state) return;
        stage.setPointerCapture(event.pointerId);
        pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
        if (pointers.size === 2) pinch = { start: spread(), zoom: zoomValue };
        stage.classList.add('is-dragging');
      });
      stage.addEventListener('pointermove', event => {
        const last = pointers.get(event.pointerId);
        if (!last || !state) return;
        const dx = event.clientX - last.x, dy = event.clientY - last.y;
        pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
        if (pointers.size >= 2 && pinch) setZoom(pinch.zoom * spread() / pinch.start);
        else if (pointers.size === 1) move(dx, dy);
      });
      const release = event => {
        pointers.delete(event.pointerId);
        pinch = null;
        if (pointers.size === 1) { /* one finger left: carry on dragging from where it is */ }
        if (!pointers.size) stage.classList.remove('is-dragging');
      };
      stage.addEventListener('pointerup', release);
      stage.addEventListener('pointercancel', release);
      stage.addEventListener('wheel', event => {
        if (!state) return;
        event.preventDefault();
        setZoom(zoomValue - event.deltaY / 300);
      }, { passive: false });
      zoom.addEventListener('input', () => { if (state) setZoom(Number(zoom.value)); });
      cancel.addEventListener('click', discard);
      use.addEventListener('click', accept);
      modal.addEventListener('pointerdown', event => { if (event.target === modal) discard(); });
      document.addEventListener('keydown', onKey, true);

      image.onload = () => {
        const { W, H } = size();
        const nw = image.naturalWidth, nh = image.naturalHeight;
        const first = layout(nw, nh, W, H, 1, 0, 0);
        state = layout(nw, nh, W, H, 1, (W - first.width) / 2, (H - first.height) / 2);
        paint();
        stage.focus({ preventScroll: true });
      };
      image.onerror = () => { close(false); };      // not a picture the browser can show: send the file as it is
      document.body.classList.add('crop-open');
      document.body.append(modal);
      image.src = url;
    }

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file || !file.type.startsWith('image/')) { chip.hidden = true; source = null; return; }
      edit(file, true);
    });
    again.addEventListener('click', async () => {
      if (source) { edit(source, false); return; }
      if (!currentSrc) return;
      try {
        const response = await fetch(currentSrc, { credentials: 'same-origin' });
        const blob = await response.blob();
        source = new File([blob], 'current.jpg', { type: blob.type || 'image/jpeg' });
        edit(source, false);
      } catch (error) { /* offline: leave the picture as it is */ }
    });
  }

  window.cropLayout = { layout, zoomAround };
  window.initializeCrop = () => document.querySelectorAll('input[type=file][data-crop-aspect]').forEach(setup);
  window.initializeCrop();
})();
