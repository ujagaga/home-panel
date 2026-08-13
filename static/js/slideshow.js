document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('slideshow_container');
  if (!container) return;

  const key = container.dataset.key;
  const url = key ? `/slideshow.json?key=${encodeURIComponent(key)}` : '/slideshow.json';
  const intervalMs = (Number(container.dataset.interval) || 1) * 60 * 1000;
  const img = document.createElement('img');
  container.appendChild(img);

  let images = [];
  let index = 0;

  function showCurrent() {
    if (images.length) {
      img.src = images[index];
    }
  }

  function fetchImages() {
    fetch(url).then(r => r.json()).then(data => {
      images = (data.enabled && data.images) || [];
      if (images.length && !img.src) {
        showCurrent();
      }
    }).catch(() => {});
  }

  function showNext() {
    if (!images.length) return;
    index = (index + 1) % images.length;
    showCurrent();
  }

  fetchImages();
  setInterval(showNext, intervalMs);
  setInterval(fetchImages, 15 * 60 * 1000);
});
