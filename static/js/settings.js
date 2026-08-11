document.addEventListener('DOMContentLoaded', function () {
  const fontSelect = document.getElementById('clock_font');
  const weightSelect = document.getElementById('clock_font_weight');
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
  }

  fontSelect.addEventListener('change', updatePreview);
  weightSelect.addEventListener('change', updatePreview);
  updatePreview();
});
