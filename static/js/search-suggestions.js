(() => {
  const form = document.querySelector('[data-product-search]');
  if (!form) return;
  const input = form.querySelector('input[name=q]');
  const panel = form.querySelector('.search-suggestions');
  const list = form.querySelector('[role=listbox]');
  const message = form.querySelector('.search-message');
  const status = form.querySelector('[role=status]');
  const viewAll = form.querySelector('.search-view-all');
  let timer, controller, generation = 0, selected = -1;
  const close = () => {
    clearTimeout(timer);
    controller?.abort();
    generation++;
    panel.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    selected = -1;
  };
  const activate = index => {
    const options = Array.from(list.children);
    selected = index;
    options.forEach((option, position) => option.setAttribute('aria-selected', String(position === index)));
    if (options[index]) {
      input.setAttribute('aria-activedescendant', options[index].id);
      options[index].scrollIntoView({block: 'nearest'});
    }
  };
  const search = async () => {
    close();
    const query = input.value.trim();
    if (!query) { status.textContent = ''; return; }
    const ticket = generation;
    controller = new AbortController();
    status.textContent = 'Finding products…';
    try {
      const response = await fetch(`${form.dataset.suggestionsUrl}?q=${encodeURIComponent(query)}`, {signal: controller.signal, credentials: 'same-origin'});
      if (!response.ok || response.redirected) throw new Error('Search unavailable');
      const data = await response.json();
      if (ticket !== generation || document.activeElement !== input) return;
      list.replaceChildren();
      data.results.forEach((product, index) => {
        const option = document.createElement('a');
        option.href = product.url;
        option.id = `product-suggestion-${index}`;
        option.setAttribute('role', 'option');
        option.setAttribute('aria-selected', 'false');
        option.tabIndex = -1;
        const image = document.createElement('img');
        image.src = product.image; image.alt = ''; image.width = 48; image.height = 48;
        const copy = document.createElement('span'); copy.className = 'suggestion-copy';
        const title = document.createElement('strong'); title.textContent = product.name;
        const detail = document.createElement('small');
        detail.textContent = [product.category, product.badge].filter(Boolean).join(' · ');
        const price = document.createElement('span'); price.className = 'suggestion-price';
        price.textContent = [product.price_prefix, product.price].filter(Boolean).join(' ');
        copy.append(title, detail, price); option.append(image, copy); list.append(option);
      });
      message.textContent = data.results.length ? 'Suggested products' : 'No matching products. Try another name or collection.';
      viewAll.href = `${form.action}?q=${encodeURIComponent(query)}`;
      viewAll.textContent = 'View all search results →';
      status.textContent = data.results.length ? `${data.results.length} suggestions shown. Use the arrow keys to choose a product.` : message.textContent;
      panel.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    } catch (error) {
      if (error.name !== 'AbortError' && ticket === generation) {
        status.textContent = 'Suggestions are unavailable. Press Enter to search.';
      }
    }
  };
  input.addEventListener('input', () => {
    close();
    status.textContent = '';
    if (input.value.trim()) timer = setTimeout(search, 180);
  });
  input.addEventListener('focus', () => { if (input.value.trim()) timer = setTimeout(search, 180); });
  input.addEventListener('keydown', event => {
    if (event.key === 'Escape') { close(); return; }
    if (panel.hidden) return;
    const count = list.children.length;
    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && count) {
      event.preventDefault();
      activate(event.key === 'ArrowDown' ? (selected + 1) % count : (selected <= 0 ? count - 1 : selected - 1));
    } else if (event.key === 'Enter' && selected >= 0) {
      event.preventDefault(); window.location.assign(list.children[selected].href);
    }
  });
  document.addEventListener('pointerdown', event => { if (!form.contains(event.target)) close(); });
  form.addEventListener('focusout', () => setTimeout(() => { if (!form.contains(document.activeElement)) close(); }, 0));
  form.addEventListener('submit', close);
})();
