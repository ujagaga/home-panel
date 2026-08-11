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
});
