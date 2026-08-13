const DIGIT_IDS = ['h1', 'h2', 'm1', 'm2'];

function updateClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const digits = hh + mm;
  DIGIT_IDS.forEach((id, i) => {
    document.getElementById(id).textContent = digits[i];
  });
}

function fitClockToWindow() {
  const clockEl = document.querySelector('.clock');
  const wrapperEl = document.querySelector('.clock_wrapper');
  const digitEls = DIGIT_IDS.map(id => document.getElementById(id));
  const padding = 0.02; // 2% of the available width/height on each side
  const wrapperRect = wrapperEl.getBoundingClientRect();
  const availableWidth = wrapperRect.width * (1 - 2 * padding);
  const availableHeight = wrapperRect.height * (1 - 2 * padding);

  const baseline = 100; // px, used just to measure at a known scale
  clockEl.style.fontSize = baseline + 'px';
  digitEls.forEach(el => {
    el.style.display = 'inline-block';
    el.style.textAlign = 'center';
    el.style.width = 'auto';
  });

  // Some display fonts aren't truly monospace, so digit widths can differ
  // (e.g. "1" narrower than "8"). Find the widest one and size every slot to
  // fit it, so the layout width stays constant no matter which digits show.
  const savedDigits = digitEls.map(el => el.textContent);
  let widestDigit = '0';
  let maxDigitWidth = 0;
  for (let d = 0; d <= 9; d++) {
    digitEls[0].textContent = String(d);
    const w = digitEls[0].getBoundingClientRect().width;
    if (w > maxDigitWidth) {
      maxDigitWidth = w;
      widestDigit = String(d);
    }
  }

  // Worst case: every slot showing the widest digit. Measuring the whole
  // clock at once naturally accounts for letter-spacing between characters.
  digitEls.forEach(el => { el.textContent = widestDigit; });
  const worstCaseRect = clockEl.getBoundingClientRect();
  digitEls.forEach((el, i) => { el.textContent = savedDigits[i]; });

  const scale = Math.min(availableWidth / worstCaseRect.width, availableHeight / worstCaseRect.height);
  clockEl.style.fontSize = (baseline * scale) + 'px';
  digitEls.forEach(el => { el.style.width = (maxDigitWidth * scale) + 'px'; });
}

updateClock();
fitClockToWindow();
setInterval(updateClock, 1000);
window.addEventListener('resize', fitClockToWindow);
if (document.fonts) {
  document.fonts.ready.then(fitClockToWindow);
}
