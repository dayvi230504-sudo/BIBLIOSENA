// JS ligero para carrusel y dropdown
(function(){
  const track = document.getElementById('carouselTrack');
  const viewport = document.getElementById('carouselViewport');
  const prev = document.getElementById('prevBtn');
  const next = document.getElementById('nextBtn');
  const step = 260; // ancho aprox de una card

  function getMaxScroll(){
    return Math.max(0, track.scrollWidth - track.clientWidth);
  }

  function bindButtons(){
    if (!track) return;
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    // El elemento que tiene overflow y scrollbar es el track
    if (prevBtn) prevBtn.onclick = () => {
      const atStart = track.scrollLeft <= 4;
      if (atStart) {
        track.scrollTo({ left: getMaxScroll(), behavior: 'smooth' });
      } else {
        track.scrollBy({ left: -step, behavior: 'smooth' });
      }
    };
    if (nextBtn) nextBtn.onclick = () => {
      const max = getMaxScroll();
      const atEnd = track.scrollLeft >= max - 4;
      if (atEnd) {
        track.scrollTo({ left: 0, behavior: 'smooth' });
      } else {
        track.scrollBy({ left: step, behavior: 'smooth' });
      }
    };
  }
  bindButtons();

  // Recalcular al cambiar tamaño para que getMaxScroll sea correcto
  window.addEventListener('resize', () => {
    // no-op: getMaxScroll se evalúa en cada click
  });

  const dropdown = document.querySelector('.dropdown');
  const toggle = document.getElementById('catToggle');
  if (dropdown && toggle) {
    toggle.addEventListener('click', () => {
      dropdown.classList.toggle('open');
    });
    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target)) dropdown.classList.remove('open');
    });
  }
})();


