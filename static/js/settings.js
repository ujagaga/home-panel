document.addEventListener('DOMContentLoaded', function () {
  const fontSelect = document.getElementById('clock_font');
  const weightSelect = document.getElementById('clock_font_weight');
  const patternSelect = document.getElementById('clock_pattern');
  const colorInput = document.getElementById('clock_pattern_color');
  const bgColorInput = document.getElementById('clock_pattern_bg_color');
  const sizeSelect = document.getElementById('clock_pattern_size');
  const bgRow = document.getElementById('clock_pattern_bg_row');
  const sizeRow = document.getElementById('clock_pattern_size_row');
  const preview = document.getElementById('clock_font_preview');

  function loadGoogleFont(query) {
    if (!query) return;
    const id = 'google-font-' + query;
    if (document.getElementById(id)) return;
    const link = document.createElement('link');
    link.id = id;
    link.rel = 'stylesheet';
    link.href = `https://fonts.googleapis.com/css2?family=${query}:wght@300;400;500;600;700;800;900&display=swap`;
    document.head.appendChild(link);
  }

  function updatePreview() {
    const fontOption = fontSelect.options[fontSelect.selectedIndex];

    loadGoogleFont(fontOption.dataset.googleFont);

    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    preview.textContent = `${hours}:${minutes}`;
    preview.style.fontFamily = `'${fontOption.value}', monospace`;
    preview.style.fontWeight = weightSelect.value;

    const patternOption = patternSelect.options[patternSelect.selectedIndex];
    const isSolid = patternOption.value === 'Solid';
    bgRow.style.display = isSolid ? 'none' : '';
    sizeRow.style.display = isSolid ? 'none' : '';

    const bgColor = isSolid ? colorInput.value : bgColorInput.value;
    const tile = Math.round(patternOption.dataset.tile * sizeSelect.value / 100);
    const params = new URLSearchParams({
      name: patternOption.value,
      color: colorInput.value,
      bg_color: bgColor
    });
    preview.style.backgroundImage = `url(/pattern.svg?${params.toString()})`;
    preview.style.backgroundSize = `${tile}px ${tile}px`;
  }

  fontSelect.addEventListener('change', updatePreview);
  weightSelect.addEventListener('change', updatePreview);
  patternSelect.addEventListener('change', updatePreview);
  colorInput.addEventListener('input', updatePreview);
  bgColorInput.addEventListener('input', updatePreview);
  sizeSelect.addEventListener('change', updatePreview);
  updatePreview();

  // Weather: pasting a Google Maps link fills the lat/lon fields, which stay
  // editable and are what actually gets saved (a blank/unrecognized link
  // never touches them).
  const weatherUrlInput = document.getElementById('weather_url');
  const weatherLatInput = document.getElementById('weather_lat');
  const weatherLonInput = document.getElementById('weather_lon');

  if (weatherUrlInput && weatherLatInput && weatherLonInput) {
    function extractLatLon(url) {
      // A URL can embed several !3d..!4d.. pairs (e.g. a breadcrumb city
      // reference before the actual pinned address) — the real place is the
      // LAST one, not the first. Falls back to q=lat,lon, then the map's
      // current center (@lat,lon,zoom), which is the least precise.
      const pinMatches = [...url.matchAll(/!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/g)];
      if (pinMatches.length) {
        const last = pinMatches[pinMatches.length - 1];
        return [last[1], last[2]];
      }
      const q = url.match(/[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)/);
      if (q) return [q[1], q[2]];
      const at = url.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
      if (at) return [at[1], at[2]];
      return null;
    }

    weatherUrlInput.addEventListener('input', function () {
      const latlon = extractLatLon(weatherUrlInput.value);
      if (latlon) {
        weatherLatInput.value = Number(latlon[0]).toFixed(4);
        weatherLonInput.value = Number(latlon[1]).toFixed(4);
      }
    });
  }
});
