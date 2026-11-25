document.documentElement.classList.add('js-ready');
const legacy = document.querySelector('#legacy-link');
if (legacy) {
  const destination = new URL(legacy.href);
  destination.search = location.search;
  if (location.hash) destination.hash = location.hash;
  legacy.href = destination.href;
  location.replace(destination.href);
} else {
  const people = document.querySelector('#people');
  const rows = [...document.querySelectorAll('.directory-row')];
  const form = document.querySelector('#directory-filters');
  const search = document.querySelector('#name-search');
  const role = document.querySelector('#role-filter');
  const decade = document.querySelector('#decade-filter');
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[’']/g, '').replace(/ø/g,'o').replace(/ł/g,'l');
  function episodesFor(row) {
    try {
      const episodes = JSON.parse(row.dataset.episodes || '[]');
      if (Array.isArray(episodes) && episodes.length) return episodes;
    } catch (_) {}
    return [{role:row.dataset.role, start:row.dataset.start ? Number(row.dataset.start):null, end:row.dataset.end ? Number(row.dataset.end):null}];
  }
  function writeDirectoryURL() {
    const next = new URL(location.href);
    next.searchParams.delete('view');
    for (const [key,value] of [['q',search.value],['role',role.value],['decade',decade.value]]) {
      if (value) next.searchParams.set(key,value); else next.searchParams.delete(key);
    }
    history.replaceState(null, '', next);
  }
  function applyFilters(update = true) {
    const query = normalize(search.value.trim());
    let visible = 0;
    for (const row of rows) {
      const episodes = episodesFor(row).filter(e => !role.value || e.role === role.value);
      const periodMatches = episodes.some(e => {
        if (!decade.value) return true;
        if (decade.value === 'undated') return e.start == null && e.end == null;
        if (e.start == null && e.end == null) return false;
        const lo = Number(decade.value), hi = lo + 9;
        return (e.start ?? e.end) <= hi && (e.end ?? 2026) >= lo;
      });
      row.hidden = !(normalize(row.dataset.name).includes(query) && periodMatches);
      if (!row.hidden) visible++;
    }
    const total = rows.length;
    document.querySelector('#result-count').textContent = `${visible} ${visible === 1 ? 'person' : 'people'}${visible === total ? '' : ` of ${total}`} in the roster`;
    document.querySelector('#no-results').hidden = visible !== 0;
    if (update) writeDirectoryURL();
  }
  function readDirectoryURL() {
    const url = new URL(location.href);
    for (const [input,param] of [[search,'q'],[role,'role'],[decade,'decade']]) input.value = url.searchParams.get(param) || '';
    applyFilters(false);
    if (url.searchParams.has('view')) {
      url.searchParams.delete('view');
      history.replaceState(null, '', url);
    }
  }
  if (people && form) {
    form.addEventListener('submit',event=>{ event.preventDefault(); applyFilters(); });
    form.addEventListener('input',()=>applyFilters());
    form.addEventListener('change',()=>applyFilters());
    form.addEventListener('reset',()=>setTimeout(()=>applyFilters(),0));
    readDirectoryURL();
  }
  function revealHash(scroll = true) {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    if (['research','history','photographs'].includes(id)) {
      id = 'people';
      const next = new URL(location.href); next.hash = id;
      history.replaceState(null, '', next);
    }
    const target = document.getElementById(id);
    if (!target) return;
    if (target.matches('.directory-row') && target.hidden) {
      search.value = ''; role.value = ''; decade.value = '';
      applyFilters();
    }
    let ancestor = target;
    while (ancestor) {
      if (ancestor.tagName === 'DETAILS') ancestor.open = true;
      ancestor = ancestor.parentElement;
    }
    if (scroll) requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));
  }
  document.addEventListener('click',event=>{
    const link = event.target.closest('a[href]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const destination = new URL(link.href);
    if (destination.origin !== location.origin || destination.pathname !== location.pathname || !destination.hash) return;
    let target;
    try { target = document.getElementById(decodeURIComponent(destination.hash.slice(1))); } catch (_) { return; }
    if (!target) return;
    event.preventDefault();
    history.pushState(null, '', destination);
    readDirectoryURL();
    revealHash();
    const focusTarget = target.matches('details') ? target.querySelector('summary') : target;
    focusTarget.focus({preventScroll:true});
  });
  window.addEventListener('popstate',()=>{ readDirectoryURL(); revealHash(); });
  window.addEventListener('hashchange',()=>revealHash());
  revealHash();
}
