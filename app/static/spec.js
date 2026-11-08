(() => {
  'use strict';
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;

  const getSaved = () => localStorage.getItem('pc_theme') || 'dark';

  const apply = (theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    btn.textContent = '';
    const isDark = theme === 'dark';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('width', '14');
    svg.setAttribute('height', '14');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');

    if (isDark) {
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', '12'); circle.setAttribute('cy', '12'); circle.setAttribute('r', '4');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', 'M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41');
      svg.append(circle, path);
    } else {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', 'M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z');
      svg.append(path);
    }
    btn.append(svg, document.createTextNode(isDark ? 'Light mode' : 'Dark mode'));
    btn.setAttribute('aria-label', `Switch to ${isDark ? 'light' : 'dark'} mode`);
  };

  apply(getSaved());

  btn.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    localStorage.setItem('pc_theme', cur);
    apply(cur);
  });
})();

