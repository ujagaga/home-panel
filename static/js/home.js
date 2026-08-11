function updateClock() {
  const now = new Date();
  document.getElementById('hours').textContent = String(now.getHours()).padStart(2, '0');
  document.getElementById('minutes').textContent = String(now.getMinutes()).padStart(2, '0');
}

function fitClockToWindow() {
  const clockEl = document.querySelector('.clock');
  const padding = 0.02; // 2% of window width/height on each side
  const availableWidth = window.innerWidth * (1 - 2 * padding);
  const availableHeight = window.innerHeight * (1 - 2 * padding);

  const baseline = 100; // px, used just to measure the text's aspect ratio
  clockEl.style.fontSize = baseline + 'px';
  const rect = clockEl.getBoundingClientRect();

  const scale = Math.min(availableWidth / rect.width, availableHeight / rect.height);
  clockEl.style.fontSize = (baseline * scale) + 'px';
}

updateClock();
fitClockToWindow();
setInterval(updateClock, 1000);
window.addEventListener('resize', fitClockToWindow);
if (document.fonts) {
  document.fonts.ready.then(fitClockToWindow);
}
