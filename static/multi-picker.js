// Copyright © 2026 Xander Chen. All rights reserved.
/* Search-and-pick for a multiple <select data-multi-picker>: type to filter, click to add, chips show what is chosen.
   The original select stays in the form and is kept in step, so the server receives exactly what it did before and
   nothing needs Ctrl. Without JavaScript the plain list still works. */
(() => {
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function setup(select) {
    if (select.dataset.pickerReady) return;
    select.dataset.pickerReady = '1';
    const noun = select.dataset.multiPicker || 'items';
    const options = [...select.options];
    const wrap = el('div', 'picker');
    const search = el('input', 'picker-search');
    search.type = 'search';
    search.placeholder = 'Search ' + noun + '…';
    search.autocomplete = 'off';
    search.setAttribute('aria-label', 'Search ' + noun);
    search.setAttribute('aria-controls', select.id + '-results');
    const results = el('ul', 'picker-results');
    results.id = select.id + '-results';
    results.setAttribute('role', 'listbox');
    results.setAttribute('aria-multiselectable', 'true');
    const chips = el('ul', 'picker-chips');
    chips.setAttribute('aria-label', 'Selected ' + noun);
    chips.setAttribute('aria-live', 'polite');
    const genres = [...new Set(options.flatMap(o => (o.dataset.genres || '').split('|').filter(Boolean)))].sort();
    let genre = '';
    const filters = el('div', 'picker-filters');
    filters.setAttribute('role', 'group');
    filters.setAttribute('aria-label', 'Filter ' + noun + ' by genre');
    if (genres.length) {
      for (const name of ['', ...genres]) {
        const button = el('button', 'picker-filter', name || 'All genres');
        button.type = 'button';
        button.dataset.genre = name;
        button.setAttribute('aria-pressed', String(name === genre));
        button.addEventListener('click', () => {
          genre = name;
          for (const other of filters.children) other.setAttribute('aria-pressed', String(other.dataset.genre === genre));
          render();
        });
        filters.append(button);
      }
    }
    wrap.append(search, filters, results, chips);
    select.insertAdjacentElement('afterend', wrap);
    select.hidden = true;
    select.style.display = 'none';

    function toggle(option) {
      option.selected = !option.selected;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      render();
    }

    function render() {
      const query = search.value.trim().toLowerCase();
      results.replaceChildren();
      let shown = 0;
      for (const option of options) {
        if (option.hidden || option.disabled) continue;                 // hidden by another filter, such as tags by category
        if (query && !option.text.toLowerCase().includes(query)) continue;
        if (genre && !(option.dataset.genres || '').split('|').includes(genre)) continue;
        const item = el('li', 'picker-option' + (option.selected ? ' is-picked' : ''));
        item.append(el('span', 'picker-name', option.text));
        if (option.dataset.genres) item.append(el('small', 'picker-genres', option.dataset.genres.split('|').join(' · ')));
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', String(option.selected));
        item.tabIndex = -1;
        item.addEventListener('mousedown', event => event.preventDefault());   // keep focus in the search box
        item.addEventListener('click', () => toggle(option));
        results.append(item);
        shown += 1;
      }
      if (!shown) results.append(el('li', 'picker-none', 'No ' + noun + ' match' + (genre ? ' in ' + genre : '') + '.'));
      chips.replaceChildren();
      for (const option of options.filter(o => o.selected && !o.disabled)) {
        const chip = el('li', 'picker-chip');
        chip.append(el('span', '', option.text));
        const remove = el('button', '', '×');
        remove.type = 'button';
        remove.setAttribute('aria-label', 'Remove ' + option.text);
        remove.addEventListener('click', () => toggle(option));
        chip.append(remove);
        chips.append(chip);
      }
      if (!chips.children.length) chips.append(el('li', 'picker-empty', 'None selected yet.'));
    }

    select.addEventListener('change', render);                      // something else changed the choices
    search.addEventListener('input', render);
    search.addEventListener('keydown', event => {
      if (event.key === 'Enter') {                       // Enter picks the first match instead of submitting the form
        event.preventDefault();
        const first = results.querySelector('.picker-option');
        if (first) first.click();
      }
    });
    select.form && select.form.addEventListener('reset', () => setTimeout(render, 0));
    render();
  }

  window.initializePickers = () => document.querySelectorAll('select[data-multi-picker]').forEach(setup);
  window.initializePickers();
})();
