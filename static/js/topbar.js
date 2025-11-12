// Script de cabecera compartida: gestiona nombre del usuario, menú y enlaces dinámicos.
(function () {
  function parseUserData(raw) {
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (_) {
      return null;
    }
  }

  function showElement(el, display = 'inline-block') {
    if (el) {
      el.style.display = display;
    }
  }

  function hideMenu(menu, container) {
    if (menu) {
      menu.style.display = 'none';
    }
    if (container) {
      container.setAttribute('aria-expanded', 'false');
    }
  }

  async function fetchUserData(userId) {
    try {
      const res = await fetch(`/api/usuarios/${userId}`);
      if (!res.ok) return null;
      const data = await res.json();
      if (data && data.nombre) {
        localStorage.setItem('userData', JSON.stringify({ id: data.id, nombre: data.nombre, name: data.nombre, documento: data.documento }));
      }
      return data;
    } catch (err) {
      console.error('Error obteniendo datos de usuario:', err);
      return null;
    }
  }

  async function loadUserName(nombreEl) {
    if (!nombreEl) return;

    const token = localStorage.getItem('token');

    if (!token) {
      nombreEl.textContent = 'Invitado';
      return;
    }

    if (token === 'admin-token') {
      nombreEl.textContent = 'Administrador';
      return;
    }

    if (!token.startsWith('user-')) {
      nombreEl.textContent = 'Usuario';
      return;
    }

    const cached = parseUserData(localStorage.getItem('userData'));
    if (cached && (cached.name || cached.nombre)) {
      nombreEl.textContent = cached.name || cached.nombre;
      return;
    }

    const userId = token.replace('user-', '');
    const fetched = await fetchUserData(userId);
    if (fetched && fetched.nombre) {
      nombreEl.textContent = fetched.nombre;
    } else {
      nombreEl.textContent = 'Usuario';
    }
  }

  function prepareLinks(token) {
    const adminLink = document.getElementById('adminLink');
    const linkMensajes = document.getElementById('linkMensajes');
    const linkMisPrestamos = document.getElementById('linkMisPrestamos');
    const linkFavoritosMenu = document.getElementById('linkFavoritosMenu');
    const accesoMisPrestamos = document.getElementById('accesoMisPrestamos');

    if (token === 'admin-token') {
      showElement(adminLink);
    } else if (token && token.startsWith('user-')) {
      showElement(linkMensajes);
      showElement(linkMisPrestamos);
      // Mantener Favoritos solo en el menú desplegable
      showElement(accesoMisPrestamos, 'block');
    }
  }

  function setupMenuInteractions(container, menu) {
    if (!container || !menu) return;
    if (container.dataset.topbarMenuInit === '1') return;

    container.dataset.topbarMenuInit = '1';

    container.addEventListener('click', (ev) => {
      ev.stopPropagation();
      const isOpen = menu.style.display === 'block';
      if (isOpen) {
        hideMenu(menu, container);
      } else {
        menu.style.display = 'block';
        menu.style.position = '';
        menu.style.top = '';
        menu.style.right = '';
        container.setAttribute('aria-expanded', 'true');
      }
    });

    document.addEventListener('click', (ev) => {
      if (!container.contains(ev.target) && !menu.contains(ev.target)) {
        hideMenu(menu, container);
      }
    });

    menu.addEventListener('click', (ev) => ev.stopPropagation());
  }

  function setupMenuActions(menu, container) {
    const linkPerfil = document.getElementById('linkPerfil');
    const linkFavoritos = document.getElementById('linkFavoritos');
    const linkCerrar = document.getElementById('linkCerrarSesion');

    if (linkPerfil && !linkPerfil.dataset.topbarActionInit) {
      linkPerfil.dataset.topbarActionInit = '1';
      linkPerfil.addEventListener('click', (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        hideMenu(menu, container);
        window.location.href = 'perfil.html';
      });
    }

    if (linkFavoritos && !linkFavoritos.dataset.topbarActionInit) {
      linkFavoritos.dataset.topbarActionInit = '1';
      linkFavoritos.addEventListener('click', (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        hideMenu(menu, container);
        window.location.href = 'favoritos.html';
      });
    }

    if (linkCerrar && !linkCerrar.dataset.topbarActionInit) {
      linkCerrar.dataset.topbarActionInit = '1';
      linkCerrar.addEventListener('click', async (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const confirmacion = await Swal.fire({
          icon: 'question',
          title: 'Cerrar sesión',
          text: '¿Estás seguro de que quieres cerrar sesión?',
          showCancelButton: true,
          confirmButtonText: 'Sí, cerrar sesión',
          cancelButtonText: 'Cancelar',
          confirmButtonColor: '#d33',
          cancelButtonColor: '#3085d6'
        });

        if (!confirmacion.isConfirmed) return;

        localStorage.removeItem('token');
        localStorage.removeItem('userData');
        localStorage.removeItem('miId');
        hideMenu(menu, container);
        setTimeout(() => {
          window.location.replace('login.html');
        }, 100);
      });
    }
  }

  function setupResponsiveDrawer(nav) {
    const toggle = document.getElementById('menuToggle');
    const overlay = document.getElementById('menuOverlay');
    if (!nav || !toggle || !overlay) return;

    nav.style.zIndex = '2200';
    overlay.style.zIndex = '2100';

    toggle.setAttribute('aria-expanded', 'false');

    const closeDrawer = () => {
      nav.classList.remove('is-open');
      overlay.classList.remove('is-active');
      toggle.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('nav-open');
    };

    const openDrawer = () => {
      nav.classList.add('is-open');
      overlay.classList.add('is-active');
      toggle.setAttribute('aria-expanded', 'true');
      document.body.classList.add('nav-open');
    };

    toggle.addEventListener('click', (ev) => {
      ev.stopPropagation();
      if (nav.classList.contains('is-open')) {
        closeDrawer();
      } else {
        openDrawer();
      }
    });

    overlay.addEventListener('click', closeDrawer);

    window.addEventListener('resize', () => {
      if (window.innerWidth > 1024) {
        closeDrawer();
      }
    });

    nav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 1024) {
          closeDrawer();
        }
      });
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeDrawer();
      }
    });
  }

  async function initializeTopbar() {
    const container = document.getElementById('usuarioContainer');
    const nombreEl = document.getElementById('nombreUsuario');
    const menu = document.getElementById('usuarioMenu');
    const nav = document.querySelector('.menu.menu--global');

    if (!container || !nombreEl || !menu || !nav) return;

    if (container.dataset.topbarInitialized === '1') {
      return;
    }
    container.dataset.topbarInitialized = '1';

    const token = localStorage.getItem('token');

    prepareLinks(token);
    await loadUserName(nombreEl);
    setupMenuInteractions(container, menu);
    setupMenuActions(menu, container);
    setupResponsiveDrawer(nav);

    if (!token) {
      nombreEl.textContent = 'Invitado';
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initializeTopbar();
  });

  window.initializeTopbar = initializeTopbar;
})();

