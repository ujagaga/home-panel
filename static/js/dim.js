document.addEventListener('DOMContentLoaded', function () {
  const overlay = document.getElementById('dim_overlay');
  if (!overlay) return;

  const startHour = Number(overlay.dataset.start);
  const endHour = Number(overlay.dataset.end);
  const opacity = Number(overlay.dataset.level) / 100;

  function isDimHour(hour) {
    if (startHour === endHour) return false;
    if (startHour < endHour) {
      return hour >= startHour && hour < endHour;
    }
    return hour >= startHour || hour < endHour; // wraps past midnight
  }

  function updateDim() {
    overlay.style.opacity = isDimHour(new Date().getHours()) ? opacity : 0;
  }

  updateDim();
  setInterval(updateDim, 60 * 1000);
});
