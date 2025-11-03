// Helpers compartidos para la app: toasts y favoritos
(function(){
  // Mostrar toast global si no existe
  if (!window.mostrarToast) {
    window.mostrarToast = function(mensaje, tipo='info', opts={duration:3500}) {
      try {
        let container = document.getElementById('toast-container');
        if (!container) {
          container = document.createElement('div');
          container.id = 'toast-container';
          container.setAttribute('aria-live','polite');
          container.setAttribute('aria-atomic','true');
          document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = 'toast toast-' + (tipo === 'success' ? 'success' : (tipo === 'error' ? 'error' : 'info'));
        toast.innerHTML = '<button class="toast-close" aria-label="Cerrar">&times;</button>'
                        + '<div class="toast-title">'+ (tipo==='success'? 'Éxito' : tipo==='error'? 'Error' : 'Información') +'</div>'
                        + '<div class="toast-body"></div>';
        toast.querySelector('.toast-body').textContent = mensaje;
        container.appendChild(toast);
        // forzar reflow
        void toast.offsetWidth;
        toast.classList.add('toast-show');
        const closeBtn = toast.querySelector('.toast-close');
        let timeoutId = setTimeout(() => hideToast(toast), opts.duration || 3500);
        closeBtn && closeBtn.addEventListener('click', () => hideToast(toast));
        toast.addEventListener('mouseenter', () => clearTimeout(timeoutId));
        function hideToast(t) {
          if (!t) return;
          t.classList.remove('toast-show');
          setTimeout(()=>{ try{ t.remove(); }catch(e){} }, 260);
        }
      } catch(e) {
        console.error('mostrarToast error', e);
      }
    };
  }

  // Favoritos en localStorage
  window.obtenerFavoritos = function() {
    try {
      const raw = localStorage.getItem('favoritos');
      return raw ? JSON.parse(raw) : [];
    } catch(e) { return []; }
  };

  window.guardarFavoritos = function(list) {
    try { localStorage.setItem('favoritos', JSON.stringify(list)); } catch(e) { console.error('guardarFavoritos', e); }
  };

  window.toggleFavorito = function(idElemento) {
    if (!idElemento) return false;
    const favs = obtenerFavoritos();
    const idx = favs.indexOf(idElemento);
    let agregado = false;
    if (idx === -1) {
      favs.push(idElemento);
      agregado = true;
    } else {
      favs.splice(idx, 1);
      agregado = false;
    }
    guardarFavoritos(favs);
    return agregado;
  };

  window.actualizarBotonFavorito = function(idElemento) {
    try {
      const favs = obtenerFavoritos();
      const esta = favs.indexOf(idElemento) !== -1;
      // Botón en detalle suele tener id 'btnFavorito'
      const btn = document.getElementById('btnFavorito');
      if (btn) {
        if (esta) {
          btn.classList.add('favorito-activo');
          btn.title = 'Quitar de favoritos';
          // cambiar color/estrella si se desea
          btn.style.background = '#ffecec';
          btn.style.color = '#e74c3c';
        } else {
          btn.classList.remove('favorito-activo');
          btn.title = 'Agregar a favoritos';
          btn.style.background = '';
          btn.style.color = '';
        }
      }
      // Si hay botones en listas con dataset.favId, actualizarlos también
      const listBtns = document.querySelectorAll('[data-fav-id]');
      listBtns.forEach(b => {
        const id = b.getAttribute('data-fav-id');
        if (!id) return;
        if (favs.indexOf(id) !== -1) {
          b.classList.add('favorito-activo');
        } else {
          b.classList.remove('favorito-activo');
        }
      });
    } catch(e) { console.error('actualizarBotonFavorito', e); }
  };

  // Al cargar la página, actualizar visuales si hay elementos con data-fav-id
  document.addEventListener('DOMContentLoaded', () => {
    try {
      const favs = obtenerFavoritos();
      // botones en lista
      document.querySelectorAll('[data-fav-id]').forEach(b => {
        const id = b.getAttribute('data-fav-id');
        if (favs.indexOf(id) !== -1) b.classList.add('favorito-activo');
      });
    } catch(e){}
  });

})();
