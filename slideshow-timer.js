// One clock drives both the countdown and the automatic slide change.
window.createSlideshowTimer = function (container, advance, isPlaying = () => true) {
  const duration = 8000;
  const track = document.createElement('div');
  track.className = 'slideshow-countdown';
  track.setAttribute('role', 'progressbar');
  track.setAttribute('aria-label', 'Time remaining before the next slide');
  track.setAttribute('aria-valuemin', '0');
  track.setAttribute('aria-valuemax', '8');
  track.style.cssText = 'height:6px;background:#d6d0c4;border-radius:3px;overflow:hidden;margin:16px 0;width:100%';
  const bar = document.createElement('div');
  bar.style.cssText = 'height:100%;width:100%;background:var(--red,#a33c36);transform-origin:left';
  track.append(bar);
  container.append(track);
  let remaining = duration;
  let last = performance.now();
  let paused = false;
  function paint() {
    bar.style.transform = `scaleX(${remaining / duration})`;
    track.setAttribute('aria-valuenow', String(Math.ceil(remaining / 1000)));
  }
  function reset() {
    remaining = duration;
    last = performance.now();
    paint();
  }
  function blocked() {
    return document.hidden || !isPlaying() || paused;
  }
  // Reset the timestamp at visibility/modal changes so blocked time is never counted.
  document.addEventListener('visibilitychange', () => { last = performance.now(); });
  const viewer = document.querySelector('#viewer');
  if (viewer) {
    new MutationObserver(() => {
      paused = viewer.open;
      last = performance.now();
    }).observe(viewer, { attributes: true, attributeFilter: ['open'] });
  }
  function tick(now) {
    if (!blocked()) remaining = Math.max(0, remaining - (now - last));
    last = now;
    if (remaining === 0) {
      advance();
      reset();
    }
    paint();
    requestAnimationFrame(tick);
  }
  reset();
  requestAnimationFrame(tick);
  return { reset };
};
