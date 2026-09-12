(() => {
  const sort = document.querySelector('#sort-order');
  const filters = document.querySelector('#collection-filters');
  if (filters) {
    const hint = filters.querySelector('.filter-auto-note');
    if (hint) hint.hidden = false;
    // A single GET form preserves every selection and resets pagination.
    const apply = () => {
      if (filters.reportValidity()) filters.requestSubmit();
    };
    filters.addEventListener('change', apply);
    // Sorting is visually above the grid, but belongs to the same filter form.
    sort?.addEventListener('change', apply);
    const resultsStatus = document.querySelector('.filter-results-status');
    const renderedStatus = resultsStatus?.textContent;
    // Browsers can restore the just-clicked control on Back even though the
    // restored URL/results describe the previous selection. Use server defaults.
    window.addEventListener('pageshow', () => {
      setTimeout(() => {
        filters.reset();
        filters.querySelector('.apply-filters').textContent = 'Apply filters';
        if (resultsStatus) resultsStatus.textContent = renderedStatus;
      }, 0);
    });
    filters.addEventListener('submit', () => {
      const button = filters.querySelector('.apply-filters');
      button.textContent = 'Updating results…';
      const status = document.querySelector('.filter-results-status');
      if (status) status.textContent = 'Updating results…';
    });
  }
  const panel = document.querySelector('.filter-panel');
  const mobile = matchMedia('(max-width: 720px)');
  const setPanel = () => { if (panel) panel.open = !mobile.matches; };
  setPanel(); mobile.addEventListener('change', setPanel);
  const authenticated = document.body.dataset.customerAuthenticated === 'true';
  let guest = {};
  try {
    // Carry existing browser favourites forward during the brand rename.
    const legacy = localStorage.getItem('astrol-wishlist');
    if (legacy) {
      const merged = {...JSON.parse(legacy), ...JSON.parse(localStorage.getItem('ojasvirudraksha-wishlist') || '{}')};
      localStorage.setItem('ojasvirudraksha-wishlist', JSON.stringify(merged));
      localStorage.removeItem('astrol-wishlist');
    }
    const value = JSON.parse(localStorage.getItem('ojasvirudraksha-wishlist') || '{}');
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      for (const [id, item] of Object.entries(value)) {
        if (/^\d+$/.test(id) && item && typeof item.name === 'string' && typeof item.url === 'string' && /^\/product\/[a-z0-9-]+\/$/.test(item.url)) guest[id] = {...item, name: item.name.replace(/astrol/gi, 'Ojasvirudraksha'), url: item.url.replace(/astrol/g, 'ojasvirudraksha')};
      }
    }
  } catch (_) {}
  let saved = authenticated ? JSON.parse(document.querySelector('#customer-wishlist-data')?.textContent || '{}') : guest;
  const status = document.querySelector('#wishlist-status');
  const persistGuest = () => { try { localStorage.setItem('ojasvirudraksha-wishlist', JSON.stringify(saved)); } catch (_) {} };
  const updateServer = async (action, id, ids = []) => {
    const body = new URLSearchParams({action});
    if (id) body.set('product', id);
    ids.forEach(value => body.append('ids', value));
    const response = await fetch('/account/wishlist/update/', {method: 'POST', credentials: 'same-origin',
      headers: {'X-CSRFToken': document.querySelector('#wishlist-csrf input').value}, body});
    if (!response.ok || response.redirected) throw new Error('Please sign in again and retry.');
    saved = (await response.json()).items;
  };
  const remove = async id => {
    if (authenticated) await updateServer('remove', id);
    else { delete saved[id]; persistGuest(); }
    render();
  };
  const render = () => {
    const headerCount = document.querySelector('#wishlist-count');
    if (headerCount) headerCount.textContent = Object.keys(saved).length;
    const total = document.querySelector('#account-wishlist-total');
    if (total) total.textContent = Object.keys(saved).length;
    document.querySelectorAll('[data-wishlist]').forEach(button => {
      const active = Boolean(saved[button.dataset.wishlist]);
      button.setAttribute('aria-pressed', String(active));
      button.setAttribute('aria-label', `${active ? 'Remove' : 'Save'} ${button.dataset.name} ${active ? 'from' : 'to'} wishlist`);
    });
    const items = document.querySelector('#wishlist-items');
    if (!items) return;
    items.replaceChildren();
    if (!Object.keys(saved).length) {
      const empty = document.createElement('p'); empty.textContent = 'Tap a heart on any product to save it here.'; items.append(empty);
    }
    Object.entries(saved).forEach(([id, item]) => {
      const row = document.createElement('div'); row.className = 'wishlist-row';
      const link = document.createElement('a'); link.href = item.url; link.textContent = item.name;
      const button = document.createElement('button'); button.textContent = 'Remove'; button.setAttribute('aria-label', `Remove ${item.name} from wishlist`);
      button.addEventListener('click', async () => { button.disabled = true; try { await remove(id); } catch (error) { status.textContent = error.message; button.disabled = false; } });
      row.append(link, button); items.append(row);
    });
  };
  let mergeComplete = Promise.resolve();
  if (authenticated && Object.keys(guest).length) {
    mergeComplete = updateServer('merge', null, Object.keys(guest)).then(() => {
      try { localStorage.removeItem('ojasvirudraksha-wishlist'); } catch (_) {}
      render();
      if (document.querySelector('[data-wishlist-page]')) window.location.reload();
    }).catch(() => { status.textContent = 'Your browser favourites could not be synced. Please refresh to retry.'; });
  }
  document.querySelectorAll('[data-wishlist]').forEach(button => button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      await mergeComplete;
      const id = button.dataset.wishlist;
      const wasSaved = Boolean(saved[id]);
      if (authenticated) await updateServer(wasSaved ? 'remove' : 'add', id);
      else {
        if (wasSaved) delete saved[id];
        else saved[id] = {name: button.dataset.name, url: button.closest('.product-card').querySelector('.product-title').getAttribute('href')};
        persistGuest();
      }
      render();
      status.textContent = saved[id] ? `${button.dataset.name} saved to wishlist.` : `${button.dataset.name} removed from wishlist.`;
      if (authenticated && document.querySelector('[data-wishlist-page]')) window.location.reload();
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  }));
  const dialog = document.querySelector('#wishlist-dialog');
  document.querySelector('button#wishlist-button')?.addEventListener('click', () => dialog.showModal());
  dialog?.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
  render();
})();

// Display the selected option's price; the server independently validates it.
(() => {
  const select = document.querySelector('#product-variant');
  if (!select) return;
  const update = () => {
    const option = select.selectedOptions[0];
    if (option) document.querySelector('#variant-price').textContent = option.dataset.price;
  };
  select.addEventListener('change', update);
  update();
})();

// Search country options without changing the visitor's choice until submitted.
(() => {
  const panel = document.getElementById('market-selector');
  const search = document.getElementById('country-search');
  const select = document.getElementById('country-choice');
  if (!panel || !search || !select) return;
  const options = Array.from(select.options, option => option.cloneNode(true));
  search.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase();
    const chosen = select.value;
    select.replaceChildren(...options.filter(option => option.textContent.toLowerCase().includes(query)).map(option => option.cloneNode(true)));
    if (Array.from(select.options).some(option => option.value === chosen)) select.value = chosen;
    document.getElementById('country-empty').hidden = select.options.length > 0;
    panel.querySelector('button[type=submit]').disabled = !select.options.length;
  });
  document.addEventListener('click', event => { if (!panel.contains(event.target)) panel.open = false; });
  panel.addEventListener('keydown', event => { if (event.key === 'Escape') { panel.open = false; panel.querySelector('summary').focus(); } });
})();
