(() => {
  // A local SVG cannot be fetched by its HTML companion. When framed, it can
  // send its own markup to the viewer without relaxing file-origin security.
  if (document.documentElement.namespaceURI === 'http://www.w3.org/2000/svg') {
    if (parent !== window && location.hash === '#viewer-svg'
        && document.currentScript.parentNode === document.documentElement) {
      const drawing = document.documentElement.cloneNode(true);
      drawing.querySelectorAll('script').forEach(script => script.remove());
      parent.postMessage({type: 'kitchenlighting-svg',
        svg: new XMLSerializer().serializeToString(drawing)}, '*');
    }
    return;
  }

  const drawings = document.getElementById('drawings');
  const error = document.getElementById('viewer-error');
  const nav = document.querySelector('.drawing-nav');
  const originalURL = new URL(location.href);
  originalURL.hash = '';
  const originalTitle = document.title;
  const initialTarget = {
    url: originalURL,
    sources: JSON.parse(drawings.dataset.sources).map(source => new URL(source, originalURL)),
    title: originalTitle,
  };
  const targets = new Map();
  const routes = new Map();
  for (const link of nav?.querySelectorAll('a[href]') || []) {
    const url = new URL(link.getAttribute('href'), originalURL);
    const source = new URL(url);
    source.pathname = source.pathname.replace(/\.html$/, '.svg');
    const target = {
      url,
      sources: [source],
      title: link.getAttribute('aria-label') || link.textContent,
      link,
      route: url.pathname.match(/\/((?:5v|12v)\/(?:min|best))\.html$/)?.[1],
    };
    targets.set(url.href, target);
    if (target.route) routes.set(target.route, target);
  }
  let generation = 0;
  let activeLoad;
  let currentTarget;

  function readSVG(source, signal) {
    return new Promise((resolve, reject) => {
      const frame = document.createElement('iframe');
      frame.hidden = true;
      frame.setAttribute('aria-hidden', 'true');
      const url = new URL(source);
      url.hash = 'viewer-svg';
      let timer;
      function finish(svg, failure) {
        clearTimeout(timer);
        window.removeEventListener('message', receive);
        signal.removeEventListener('abort', abort);
        frame.remove();
        if (failure) reject(failure);
        else resolve(svg);
      }
      function receive(event) {
        // Local files have opaque origins. Match the specific frame instead.
        if (event.source === frame.contentWindow
            && event.data?.type === 'kitchenlighting-svg'
            && typeof event.data.svg === 'string') {
          finish(event.data.svg);
        }
      }
      function abort() {
        finish(null, new DOMException('Drawing load cancelled', 'AbortError'));
      }
      window.addEventListener('message', receive);
      signal.addEventListener('abort', abort, {once: true});
      frame.onerror = () => finish(null, new Error('Could not load SVG'));
      timer = setTimeout(() => finish(null, new Error('SVG load timed out')), 10000);
      frame.src = url.href;
      document.body.append(frame);
      if (signal.aborted) abort();
    });
  }

  function inlineSVG(source, number) {
    const parsed = new DOMParser().parseFromString(source, 'image/svg+xml');
    const root = parsed.documentElement;
    const bounds = (root.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
    if (root.localName !== 'svg' || root.namespaceURI !== 'http://www.w3.org/2000/svg'
        || parsed.querySelector('parsererror') || bounds.length !== 4
        || !bounds.every(Number.isFinite) || bounds[2] <= 0 || bounds[3] <= 0) {
      throw new Error('Invalid SVG drawing');
    }
    for (const script of root.querySelectorAll('script')) script.remove();
    const elements = [root, ...root.querySelectorAll('*')];
    const ids = new Map(elements.filter(element => element.hasAttribute('id'))
      .map(element => [element.id, `page-${number}-${element.id}`]));
    for (const element of elements) {
      for (const attribute of [...element.attributes]) {
        let value = attribute.value;
        if (attribute.name === 'id') value = ids.get(value);
        else if (attribute.localName === 'href' && value.startsWith('#')) {
          value = '#' + (ids.get(value.slice(1)) || value.slice(1));
        } else if (['aria-labelledby', 'aria-describedby'].includes(attribute.name)) {
          value = value.split(/\s+/).map(id => ids.get(id) || id).join(' ');
        } else {
          value = value.replace(/url\(#([^)]+)\)/g,
            (_, id) => `url(#${ids.get(id) || id})`);
        }
        if (value !== attribute.value) attribute.value = value;
      }
    }
    root.setAttribute('role', 'img');
    return document.importNode(root, true);
  }

  function targetFromHash() {
    const target = routes.get(location.hash.slice(1));
    if (target) return target;
    // Keep bookmarks created before the shorter fragment format working.
    const route = new URLSearchParams(location.hash.slice(1)).get('drawing');
    if (route) {
      try {
        return targets.get(new URL(route, originalURL).href) || initialTarget;
      } catch (_) {
        return initialTarget;
      }
    }
    return initialTarget;
  }

  function replaceRoute(target) {
    const route = targets.get(target.url.href)?.route;
    if (!route || !location.hash || targetFromHash().url.href !== target.url.href) return;
    const url = new URL(originalURL);
    url.hash = target.url.href === originalURL.href ? '' : route;
    if (url.href !== location.href) history.replaceState(history.state, '', url);
  }

  function pushRoute(target) {
    if (targetFromHash().url.href === target.url.href) {
      replaceRoute(target);
      return;
    }
    const url = new URL(originalURL);
    url.hash = target.url.href === originalURL.href ? '' : target.route;
    history.pushState(null, '', url);
  }

  async function showTarget(target, push = false) {
    const request = ++generation;
    activeLoad?.abort();
    error.hidden = true;
    const controller = new AbortController();
    activeLoad = controller;
    try {
      if (currentTarget?.url.href === target.url.href) {
        // A history target may still be loading behind the displayed drawing.
        if (push) pushRoute(target);
        else replaceRoute(target);
        return;
      }
      const sources = await Promise.all(target.sources.map(source => readSVG(source, controller.signal)));
      if (request !== generation) return;
      const pages = sources.map((source, index) => inlineSVG(source, index + 1));
      const svgTitle = [...pages[0].children].find(element => element.localName === 'title')?.textContent;
      const title = target === initialTarget ? originalTitle : svgTitle?.trim() || target.title;
      pages.forEach((page, index) => page.setAttribute('aria-label',
        `${title}, page ${index + 1} of ${pages.length}`));
      if (push) pushRoute(target);
      else replaceRoute(target);
      // A single DOM replacement keeps the browser's native pinch and pan.
      drawings.replaceChildren(...pages);
      document.title = title;
      currentTarget = target;
      for (const option of targets.values()) {
        if (option.url.href === target.url.href) option.link.setAttribute('aria-current', 'page');
        else option.link.removeAttribute('aria-current');
      }
    } catch (failure) {
      if (request !== generation || failure.name === 'AbortError') return;
      controller.abort();
      const link = document.createElement('a');
      link.href = target.sources[0].href;
      link.textContent = 'Open the SVG directly';
      error.replaceChildren(document.createTextNode('Could not load the drawing. '), link);
      error.hidden = false;
    }
  }

  if (nav) {
    // Drawing navigation keeps the current pan. A full reload must instead
    // restore it alongside Firefox's retained native pinch zoom.
    history.scrollRestoration = 'manual';
    window.addEventListener('pagehide', () => { history.scrollRestoration = 'auto'; });
    window.addEventListener('pageshow', () => { history.scrollRestoration = 'manual'; });
    nav.addEventListener('click', event => {
      const link = event.target.closest('a[href]');
      if (!link || event.defaultPrevented || event.button !== 0
          || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey
          || link.target || link.hasAttribute('download')) return;
      const target = targets.get(new URL(link.getAttribute('href'), originalURL).href);
      if (!target) return;
      event.preventDefault();
      showTarget(target, true);
    });
    window.addEventListener('popstate', () => showTarget(targetFromHash()));
  }
  showTarget(targetFromHash());

  const viewport = window.visualViewport;
  if (!nav || !viewport) return;
  let pending = false;
  function updateNavigation() {
    pending = false;
    if (viewport.scale <= 0 || viewport.width <= 0 || viewport.height <= 0) return;
    const inverseScale = 1 / viewport.scale;
    const style = getComputedStyle(nav);
    // Fixed positioning follows the layout viewport, while pinch zoom changes
    // the visual viewport. Move the anchor and cancel the pinch scaling.
    const x = viewport.offsetLeft + viewport.width - document.documentElement.clientWidth
      + parseFloat(style.right) * (1 - inverseScale);
    const y = viewport.offsetTop + viewport.height - document.documentElement.clientHeight
      + parseFloat(style.bottom) * (1 - inverseScale);
    nav.style.transform = `translate(${x}px, ${y}px) scale(${inverseScale})`;
  }
  function schedule() {
    if (!pending) {
      pending = true;
      requestAnimationFrame(updateNavigation);
    }
  }
  viewport.addEventListener('resize', schedule);
  viewport.addEventListener('scroll', schedule);
  window.addEventListener('resize', schedule);
  window.addEventListener('scroll', schedule);
  window.addEventListener('pageshow', schedule);
  schedule();
})();
