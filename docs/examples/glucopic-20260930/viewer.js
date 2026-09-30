/* Progressive enhancement: the complete image galleries remain usable without JS. */
(() => {
  'use strict';
  const dataElement = document.getElementById('gallery-data');
  if (!dataElement) return;
  let data;
  try { data = JSON.parse(dataElement.textContent); } catch (_) { return; }
  const views = ['pitch', 'master'];
  if (!views.every(view => data[view] && Array.isArray(data[view].slides) && data[view].slides.length)) return;
  const byId = id => document.getElementById(id);
  const elements = {
    viewer: byId('viewer'), image: byId('large-slide'), title: byId('current-title'),
    count: byId('current-count'), select: byId('slide-select'), previous: byId('previous'),
    next: byId('next'), original: byId('current-original'), download: byId('current-download'),
    permalink: byId('current-link'), largeOriginal: byId('large-original'), error: byId('image-error')
  };
  if (Object.values(elements).some(element => !element)) return;
  const switches = [...document.querySelectorAll('[data-view]')];
  const galleries = [...document.querySelectorAll('[data-gallery]')];
  const thumbnails = [...document.querySelectorAll('[data-select]')];
  let state = { view: 'pitch', index: 0 };
  let previousView = null;
  const hashFor = () => `#${state.view}-${state.index + 1}`;
  function parseHash(hash) {
    const match = /^#(pitch|master)-([1-9]\d*)$/.exec(hash);
    if (!match) return null;
    const number = Number(match[2]);
    if (!Number.isSafeInteger(number) || number > data[match[1]].slides.length) return null;
    return { view: match[1], index: number - 1 };
  }
  function writeHash() {
    if (location.hash === hashFor()) return;
    try { history.replaceState(null, '', hashFor()); } catch (_) { /* file:// and embedded viewers may restrict history */ }
  }
  function render(updateHash = true) {
    const deck = data[state.view];
    const slide = deck.slides[state.index];
    const caption = `${deck.label} ${state.index + 1}장. ${slide.title}`;
    if (previousView !== state.view) {
      elements.select.replaceChildren(...deck.slides.map((item, index) => {
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = `${String(index + 1).padStart(2, '0')} · ${item.title}`;
        return option;
      }));
      previousView = state.view;
    }
    elements.error.hidden = true;
    elements.image.alt = caption;
    elements.image.src = slide.image;
    elements.title.textContent = slide.title;
    elements.count.textContent = `${deck.label} · ${state.index + 1} / ${deck.slides.length}`;
    elements.select.value = String(state.index);
    elements.previous.disabled = state.index === 0;
    elements.next.disabled = state.index === deck.slides.length - 1;
    elements.original.href = slide.image;
    elements.original.setAttribute('aria-label', `${caption} PNG 원본 보기`);
    elements.largeOriginal.href = slide.image;
    elements.largeOriginal.setAttribute('aria-label', `${caption} PNG 원본 보기`);
    elements.download.href = slide.image;
    elements.download.download = `glucopic-${state.view}-${String(state.index + 1).padStart(2, '0')}.png`;
    elements.download.setAttribute('aria-label', `${caption} PNG 다운로드`);
    elements.permalink.href = hashFor();
    elements.permalink.setAttribute('aria-label', `${caption} 직접 링크`);
    switches.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === state.view)));
    galleries.forEach(gallery => gallery.setAttribute('aria-hidden', String(gallery.dataset.gallery !== state.view)));
    thumbnails.forEach(link => {
      const selected = link.dataset.select === `${state.view}-${state.index + 1}`;
      if (selected) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
    if (updateHash) writeHash();
  }
  function move(index) {
    const last = data[state.view].slides.length - 1;
    state.index = Math.max(0, Math.min(index, last));
    render();
  }
  function chooseView(view) {
    if (!views.includes(view) || view === state.view) return;
    const slideId = data[state.view].slides[state.index].id;
    const related = data[view].slides.findIndex(slide => slide.id === slideId);
    state = { view, index: related >= 0 ? related : 0 };
    render();
  }
  switches.forEach(button => button.addEventListener('click', () => chooseView(button.dataset.view)));
  elements.previous.addEventListener('click', () => move(state.index - 1));
  elements.next.addEventListener('click', () => move(state.index + 1));
  elements.select.addEventListener('change', () => {
    const index = Number(elements.select.value);
    if (Number.isInteger(index)) move(index);
  });
  thumbnails.forEach(link => link.addEventListener('click', event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
    const next = parseHash(`#${link.dataset.select}`);
    if (!next) return;
    event.preventDefault();
    state = next;
    render();
    elements.viewer.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    elements.largeOriginal.focus({ preventScroll: true });
  }));
  document.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.isComposing) return;
    const target = event.target;
    if (target instanceof Element && (target.closest('input, textarea, select, [contenteditable=""], [contenteditable="true"], [role="textbox"]') || target.isContentEditable)) return;
    const actions = { ArrowLeft: () => move(state.index - 1), ArrowRight: () => move(state.index + 1), Home: () => move(0), End: () => move(data[state.view].slides.length - 1) };
    if (!actions[event.key]) return;
    event.preventDefault();
    actions[event.key]();
  });
  window.addEventListener('hashchange', () => {
    const next = parseHash(location.hash);
    if (next) { state = next; render(false); }
  });
  elements.image.addEventListener('error', () => { elements.error.hidden = false; });
  elements.image.addEventListener('load', () => { elements.error.hidden = true; });
  const requested = parseHash(location.hash);
  if (requested) state = requested;
  render(false);
  document.documentElement.classList.add('enhanced');
  elements.viewer.hidden = false;
})();
