document.documentElement.classList.add('js');
addEventListener('DOMContentLoaded', () => requestAnimationFrame(() => requestAnimationFrame(() => document.documentElement.classList.add('anim'))), { once: true });
