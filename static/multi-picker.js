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
    wrap.append(search, results, chips);
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
        if (query && !option.text.toLowerCase().includes(query)) continue;
        const item = el('li', 'picker-option' + (option.selected ? ' is-picked' : ''), option.text);
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', String(option.selected));
        item.tabIndex = -1;
        item.addEventListener('mousedown', event => event.preventDefault());   // keep focus in the search box
        item.addEventListener('click', () => toggle(option));
        results.append(item);
        shown += 1;
      }
      if (!shown) results.append(el('li', 'picker-none', 'No ' + noun + ' match.'));
      chips.replaceChildren();
      for (const option of options.filter(o => o.selected)) {
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
