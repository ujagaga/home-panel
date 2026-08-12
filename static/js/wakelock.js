document.addEventListener('DOMContentLoaded', function () {
  if (!('wakeLock' in navigator)) return;

  async function requestWakeLock() {
    try {
      await navigator.wakeLock.request('screen');
    } catch (err) {
      // Ignore — e.g. battery saver mode, or not allowed in this context.
    }
  }

  requestWakeLock();

  // The lock is released automatically when the page loses visibility
  // (screen off, app switched away) and does not resume on its own.
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') {
      requestWakeLock();
    }
  });
});
