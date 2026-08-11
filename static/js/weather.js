document.addEventListener('DOMContentLoaded', function () {
  const widget = document.getElementById('weather_widget');
  if (!widget) return;

  const key = widget.dataset.key;
  const url = key ? `/weather.json?key=${encodeURIComponent(key)}` : '/weather.json';

  function render(data) {
    if (!data.available) {
      widget.style.display = 'none';
      return;
    }

    let html = `<div class="weather_current">${data.current.icon} ${data.current.temp}&deg;C</div>`;
    if (data.change) {
      html += `<div class="weather_change">${data.change.icon} ${data.change.category} expected at ${data.change.at}</div>`;
    }
    widget.innerHTML = html;
    widget.style.display = '';
  }

  function fetchWeather() {
    fetch(url).then(r => r.json()).then(render).catch(() => {});
  }

  fetchWeather();
  setInterval(fetchWeather, 15 * 60 * 1000);
});
