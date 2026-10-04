/* Tags follow the categories: only tags that belong to a selected category are offered (all of them while no category
   is chosen), and a tag whose category gets deselected is unselected so it cannot be saved by mistake. */
(() => {
  function setup(tags) {
    if (tags.dataset.filterReady) return;
    const categories = document.getElementById(tags.dataset.filterBy);
    if (!categories) return;
    tags.dataset.filterReady = '1';
    const note = document.createElement('p');
    note.className = 'filter-note';
    tags.insertAdjacentElement('afterend', note);

    function apply() {
      const chosen = new Set([...categories.selectedOptions].map(option => option.value));
      for (const option of tags.options) {
        const show = !chosen.size || chosen.has(option.dataset.category);
        option.hidden = !show;
        option.disabled = !show;                       // a hidden tag is never submitted
        if (!show) option.selected = false;
      }
      note.textContent = chosen.size ? 'Showing tags for the selected categories.' : 'Choose a category to narrow this list to its tags.';
      tags.dispatchEvent(new Event('change', { bubbles: true }));
    }

    categories.addEventListener('change', apply);
    apply();
  }

  window.initializeTagFilter = () => document.querySelectorAll('select[data-filter-by]').forEach(setup);
  window.initializeTagFilter();
})();
