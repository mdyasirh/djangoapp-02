/**
 * FitLife Studio – app.js
 * Handles language toggle (i18n) via data-attributes.
 * Default language is German (de).
 */

// ---- Language Toggle (i18n) ----

function applyLanguage(lang) {
  document.querySelectorAll('[data-en][data-de]').forEach(el => {
    const text = el.getAttribute('data-' + lang);
    if (text !== null) {
      if ((el.tagName === 'INPUT' && el.type !== 'hidden') || el.tagName === 'TEXTAREA') {
        el.value = text;
      } else {
        el.innerText = text;
      }
    }
  });
  // Update toggle button text to show current language
  const btn = document.getElementById('langToggle');
  if (btn) {
    btn.innerText = lang === 'de' ? 'DE | EN' : 'EN | DE';
  }
}

function toggleLanguage() {
  const current = localStorage.getItem('lang') || 'de';
  const next = current === 'en' ? 'de' : 'en';
  localStorage.setItem('lang', next);
  applyLanguage(next);
}

// Apply saved language on page load (default: German)
document.addEventListener('DOMContentLoaded', () => {
  const lang = localStorage.getItem('lang') || 'de';
  applyLanguage(lang);
});

// ---- Notification System ----

const NOTIFICATION_POLL_INTERVAL_MS = 30000;

async function fetchNotifications() {
  try {
    const resp = await fetch('/api/notifications/');
    const data = await resp.json();
    if (data.ok) {
      updateNotificationBadge(data.count);
      return data.notifications;
    }
  } catch (err) {
    console.warn('Failed to fetch notifications:', err);
  }
  return [];
}

function updateNotificationBadge(count) {
  const badges = document.querySelectorAll('.notification-count');
  badges.forEach(badge => {
    if (count > 0) {
      badge.textContent = count;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  });
}

async function markNotificationRead(notifId, csrf) {
  const body = new URLSearchParams({ notification_id: notifId });
  await fetch('/api/notifications/mark-read/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrf },
    body: body,
  });
}

async function markAllNotificationsRead(csrf) {
  await fetch('/api/notifications/mark-all-read/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrf },
  });
}

// Poll for notifications every 30 seconds
document.addEventListener('DOMContentLoaded', () => {
  fetchNotifications();
  setInterval(fetchNotifications, NOTIFICATION_POLL_INTERVAL_MS);
});
