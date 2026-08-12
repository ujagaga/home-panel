document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('fullscreen_btn');
  if (!btn) return;

  const icon = btn.querySelector('i');
  const HIDE_DELAY = 4000;
  let hideTimer = null;

  function showButton() {
    btn.classList.remove('hidden');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => btn.classList.add('hidden'), HIDE_DELAY);
  }

  function updateIcon() {
    icon.className = document.fullscreenElement ? 'fa-solid fa-compress' : 'fa-solid fa-expand';
  }

  btn.addEventListener('click', function () {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  });

  document.addEventListener('fullscreenchange', updateIcon);
  ['touchstart', 'mousemove', 'click'].forEach(function (evt) {
    document.addEventListener(evt, showButton);
  });

  showButton();
});
