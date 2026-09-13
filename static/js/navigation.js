(() => {
  const nav = document.querySelector('.collection-nav');
  if (!nav) return;
  const menus = [...nav.querySelectorAll('.nav-disclosure')];
  const hover = matchMedia('(hover: hover) and (pointer: fine) and (min-width: 601px)');
  let pendingClose;
  const closeOthers = current => menus.forEach(menu => { if (menu !== current) menu.open = false; });
  const position = menu => {
    const box = menu.querySelector('summary').getBoundingClientRect();
    const width = Math.min(310, window.innerWidth - 32);
    menu.style.setProperty('--dropdown-left', `${Math.max(16, Math.min(box.left, window.innerWidth - width - 16))}px`);
    menu.style.setProperty('--dropdown-top', `${box.bottom}px`);
    menu.style.setProperty('--dropdown-height', `${Math.max(100, window.innerHeight - box.bottom - 16)}px`);
  };
  menus.forEach(menu => {
    menu.addEventListener('pointerenter', () => {
      if (!hover.matches) return;
      clearTimeout(pendingClose);
      closeOthers(menu);
      position(menu);
      menu.open = true;
    });
    menu.addEventListener('pointerleave', () => {
      if (!hover.matches || menu.contains(document.activeElement)) return;
      pendingClose = setTimeout(() => { menu.open = false; }, 180);
    });
    menu.addEventListener('toggle', () => { if (menu.open) { closeOthers(menu); position(menu); } });
    menu.addEventListener('focusout', () => {
      setTimeout(() => { if (!menu.contains(document.activeElement)) menu.open = false; }, 0);
    });
    menu.querySelector('summary').addEventListener('keydown', event => {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        closeOthers(menu);
        position(menu);
        menu.open = true;
        menu.querySelector('a')?.focus();
      }
    });
  });
  nav.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      const menu = event.target.closest('.nav-disclosure');
      if (menu) { menu.open = false; menu.querySelector('summary').focus(); }
    }
  });
  document.addEventListener('pointerdown', event => { if (!nav.contains(event.target)) closeOthers(null); });
  nav.addEventListener('scroll', () => closeOthers(null));
  window.addEventListener('scroll', () => closeOthers(null), {passive: true});
  window.addEventListener('resize', () => closeOthers(null));
})();
