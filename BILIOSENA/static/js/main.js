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
  const menu = document.getElementById('catMenu');
  if (dropdown && toggle && menu) {
    // Asegurar que el menu tenga z-index MUY ALTO para estar sobre el carrusel
    menu.style.setProperty('z-index', '100000', 'important');
    menu.style.setProperty('position', 'fixed', 'important');
    menu.style.setProperty('background', '#ffffff', 'important');
    menu.style.setProperty('box-shadow', '0 20px 80px rgba(0,0,0,0.9)', 'important');
    menu.style.setProperty('isolation', 'isolate', 'important');
    
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      e.preventDefault();
      
      const isOpen = dropdown.classList.toggle('open');
      
      if (isOpen && menu) {
        // Obtener posición del botón
        const rect = toggle.getBoundingClientRect();
        
        // Aplicar todas las propiedades críticas con z-index MUY ALTO
        menu.style.setProperty('display', 'block', 'important');
        menu.style.setProperty('position', 'fixed', 'important');
        menu.style.setProperty('z-index', '100000', 'important'); // Por encima del carrusel (z-index: 1)
        menu.style.setProperty('isolation', 'isolate', 'important');
        menu.style.setProperty('top', (rect.bottom + 8) + 'px', 'important');
        menu.style.setProperty('left', rect.left + 'px', 'important');
        menu.style.setProperty('width', Math.max(280, rect.width) + 'px', 'important');
        menu.style.setProperty('opacity', '1', 'important');
        menu.style.setProperty('pointer-events', 'all', 'important');
        menu.style.setProperty('background', '#ffffff', 'important');
        menu.style.setProperty('border', '3px solid rgba(102, 126, 234, 0.6)', 'important');
        
        // Ajustar posición después de renderizar
        requestAnimationFrame(() => {
          const menuRect = menu.getBoundingClientRect();
          const viewportWidth = window.innerWidth;
          const viewportHeight = window.innerHeight;
          
          // Ajustar horizontalmente
          if (menuRect.right > viewportWidth - 10) {
            menu.style.setProperty('left', (viewportWidth - menuRect.width - 10) + 'px', 'important');
          }
          if (menuRect.left < 10) {
            menu.style.setProperty('left', '10px', 'important');
          }
          
          // Ajustar verticalmente - mostrar arriba si no cabe abajo
          if (menuRect.bottom > viewportHeight - 10) {
            menu.style.setProperty('top', (rect.top - menuRect.height - 8) + 'px', 'important');
          }
          if (menuRect.top < 10) {
            menu.style.setProperty('top', '10px', 'important');
          }
        });
      } else {
        menu.style.setProperty('display', 'none', 'important');
        menu.style.setProperty('opacity', '0', 'important');
        menu.style.setProperty('pointer-events', 'none', 'important');
      }
    });
    
    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
        if (menu) {
          menu.style.setProperty('display', 'none', 'important');
          menu.style.setProperty('opacity', '0', 'important');
          menu.style.setProperty('pointer-events', 'none', 'important');
        }
      }
    });
    
    // Cerrar al hacer scroll
    let scrollTimeout;
    window.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        dropdown.classList.remove('open');
        if (menu) {
          menu.style.setProperty('display', 'none', 'important');
          menu.style.setProperty('opacity', '0', 'important');
          menu.style.setProperty('pointer-events', 'none', 'important');
        }
      }, 150);
    }, true);
    
    // También cerrar al redimensionar
    window.addEventListener('resize', () => {
      dropdown.classList.remove('open');
      if (menu) {
        menu.style.setProperty('display', 'none', 'important');
        menu.style.setProperty('opacity', '0', 'important');
        menu.style.setProperty('pointer-events', 'none', 'important');
      }
    });
  }
})();


