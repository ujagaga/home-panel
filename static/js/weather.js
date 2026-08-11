document.addEventListener('DOMContentLoaded', function () {
  const widget = document.getElementById('weather_widget');
  if (!widget) return;

  const key = widget.dataset.key;
  const url = key ? `/weather.json?key=${encodeURIComponent(key)}` : '/weather.json';
  const scale = (Number(widget.dataset.size) || 100) / 100;

  function render(data) {
    if (!data.available) {
      widget.style.display = 'none';
      return;
    }

    let html = '';
    if (data.city) {
      html += `<div class="weather_city">${data.city}</div>`;
    }
    html += `<div class="weather_current">${data.current.icon} ${data.current.temp}&deg;C</div>`;
    if (data.change) {
      const verb = data.change.kind === 'stopping' ? 'ending' : 'expected';
      html += `<div class="weather_change">${data.change.icon} ${data.change.category} ${verb} at ${data.change.at}</div>`;
    }
    widget.innerHTML = html;
    widget.style.transform = `scale(${scale})`;
    widget.style.display = 'block';
  }

  function fetchWeather() {
    fetch(url).then(r => r.json()).then(render).catch(() => {});
  }

  fetchWeather();
  setInterval(fetchWeather, 15 * 60 * 1000);
});
