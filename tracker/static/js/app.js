/**
 * FitLife Studio – app.js
 * Handles language toggle (i18n) via data-attributes.
 */

// ---- Language Toggle (i18n) ----

function applyLanguage(lang) {
  document.querySelectorAll('[data-en][data-de]').forEach(el => {
    const text = el.getAttribute('data-' + lang);
    if (text !== null) {
      // For input elements, set value; for textareas, set value; for others, set innerText
      if (el.tagName === 'INPUT' && el.type !== 'hidden') {
        el.value = text;
      } else if (el.tagName === 'TEXTAREA') {
        el.value = text;
      } else {
        el.innerText = text;
      }
    }
  });
}

function toggleLanguage() {
  const current = localStorage.getItem('lang') || 'en';
  const next = current === 'en' ? 'de' : 'en';
  localStorage.setItem('lang', next);
  applyLanguage(next);
}

// Apply saved language on page load
document.addEventListener('DOMContentLoaded', () => {
  const lang = localStorage.getItem('lang') || 'en';
  applyLanguage(lang);
});
