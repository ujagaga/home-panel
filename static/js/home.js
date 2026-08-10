function updateClock() {
  const now = new Date();
  document.getElementById('hours').textContent = String(now.getHours()).padStart(2, '0');
  document.getElementById('minutes').textContent = String(now.getMinutes()).padStart(2, '0');
}

updateClock();
setInterval(updateClock, 1000);
