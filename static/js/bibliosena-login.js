const viewport = document.getElementById('viewport');
const toRegisterBtn = document.getElementById('toRegister');
const toLoginBtn = document.getElementById('toLogin');
const phraseElement = document.querySelector('.tagline .phrase');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

const phraseSets = {
  login: [
    'Bienvenido a BIBLIOSENA 📚',
    'Tu conocimiento comienza aquí 💡',
    'Explora, aprende y comparte 🤝'
  ],
  register: [
    'Conéctate con el aprendizaje del SENA 🚀',
    'Activa tu cuenta y aprende sin límites ✨',
    'Construye hoy tu futuro académico 📖'
  ]
};

let activeSet = 'login';
let phraseIndex = 0;
let phraseTimer;

function rotatePhrases() {
  const phrases = phraseSets[activeSet];
  phraseElement.classList.remove('current');
  phraseElement.style.animation = 'fadePhraseOut 0.6s forwards';

  setTimeout(() => {
    phraseIndex = (phraseIndex + 1) % phrases.length;
    phraseElement.textContent = phrases[phraseIndex];
    phraseElement.style.animation = 'fadePhraseIn 0.6s forwards';
    phraseElement.classList.add('current');
  }, 600);
}

function startPhraseLoop() {
  clearInterval(phraseTimer);
  phraseTimer = setInterval(rotatePhrases, 3200);
}

function setPhraseSet(setName) {
  if (activeSet === setName) return;
  activeSet = setName;
  phraseIndex = 0;
  phraseElement.classList.remove('current');
  phraseElement.style.animation = 'none';
  void phraseElement.offsetWidth; // force repaint
  phraseElement.textContent = phraseSets[activeSet][phraseIndex];
  phraseElement.style.animation = 'fadePhraseIn 0.6s forwards';
  phraseElement.classList.add('current');
  startPhraseLoop();
}

startPhraseLoop();

if (toRegisterBtn) {
  toRegisterBtn.addEventListener('click', () => {
    viewport.classList.add('register-active');
    viewport.classList.remove('initial');
    setPhraseSet('register');
  });
}

if (toLoginBtn) {
  toLoginBtn.addEventListener('click', () => {
    viewport.classList.remove('register-active');
    setPhraseSet('login');
  });
}

window.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => viewport.classList.remove('initial'), 1200);
});

const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
const applyTheme = (isDark) => {
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
};
applyTheme(prefersDark.matches);
prefersDark.addEventListener('change', (event) => applyTheme(event.matches));

if (loginForm) {
  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();

    if (!username || !password) {
      alert('Por favor completa todos los campos para iniciar sesión.');
      return;
    }

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: username, username, password })
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        localStorage.setItem('token', data.token);
        if (data.user) {
          localStorage.setItem('userData', JSON.stringify(data.user));
          localStorage.setItem('miId', data.user.id || data.user.documento || '');
        }
        window.location.href = 'principal.html';
      } else {
        alert(data.error || 'Error de autenticación. Inténtalo de nuevo.');
      }
    } catch (error) {
      alert('No se pudo iniciar sesión. Verifica tu conexión.');
    }
  });
}

if (registerForm) {
  registerForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const nombre = document.getElementById('reg-nombre').value.trim();
    const tipoDocumento = document.getElementById('reg-tipo-documento').value;
    const ficha = document.getElementById('reg-ficha').value.trim();
    const documento = document.getElementById('reg-documento').value.trim();
    const correo = document.getElementById('reg-correo').value.trim();
    const telefono = document.getElementById('reg-telefono').value.trim();
    const tipoUsuario = document.getElementById('reg-tipo-usuario').value;
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm').value;
    const acepta = document.getElementById('reg-acepta').checked;

    if (!nombre || !tipoDocumento || !ficha || !documento || !correo || !telefono || !tipoUsuario || !username || !password || !confirm) {
      alert('Por favor completa todos los campos para registrarte.');
      return;
    }

    if (password !== confirm) {
      alert('Las contraseñas no coinciden.');
      return;
    }

    if (!acepta) {
      alert('Debes aceptar los términos y condiciones.');
      return;
    }

    const payload = {
      nombre,
      tipo_documento: tipoDocumento,
      ficha,
      documento,
      correo,
      telefono,
      tipo_usuario: tipoUsuario,
      username,
      password,
      role: 'user'
    };

    try {
      const res = await fetch('/api/usuarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        alert('Usuario creado correctamente. Ya puedes iniciar sesión.');
        registerForm.reset();
        viewport.classList.remove('register-active');
        setPhraseSet('login');
      } else {
        alert(data.error || 'No se pudo registrar el usuario.');
      }
    } catch (error) {
      alert('Error de red. Inténtalo nuevamente.');
    }
  });
}

const canvas = document.getElementById('particles');
const ctx = canvas ? canvas.getContext('2d') : null;
let canvasWidth = 0;
let canvasHeight = 0;
const particles = [];
const PARTICLE_COUNT = 60;
const pointer = { x: 0, y: 0, active: false };

function resizeCanvas() {
  if (!canvas || !ctx) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvasWidth = rect.width;
  canvasHeight = rect.height;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
}

class Particle {
  constructor() {
    this.reset(true);
  }

  reset(initial = false) {
    this.x = Math.random() * canvasWidth;
    this.y = initial ? Math.random() * canvasHeight : -10;
    this.size = Math.random() * 3 + 1;
    this.speedX = (Math.random() - 0.5) * 0.35;
    this.baseSpeedY = Math.random() * 0.5 + 0.2;
    this.speedY = this.baseSpeedY;
    this.alpha = Math.random() * 0.5 + 0.2;
    this.driftOffset = Math.random() * Math.PI * 2;
  }

  update(time) {
    const drift = Math.sin(time * 0.0005 + this.driftOffset) * 0.3;
    this.x += this.speedX + drift;
    this.y += this.speedY;

    if (pointer.active) {
      const dx = pointer.x - this.x;
      const dy = pointer.y - this.y;
      const dist = Math.hypot(dx, dy);
      const influenceRadius = 160;

      if (dist < influenceRadius && dist > 0.001) {
        const force = (influenceRadius - dist) / influenceRadius;
        this.x -= (dx / dist) * force * 1.4;
        this.y -= (dy / dist) * force * 1.4;
      }
    }

    if (this.y - this.size > canvasHeight) {
      this.reset();
    }
    if (this.x - this.size > canvasWidth) this.x = -this.size;
    if (this.x + this.size < 0) this.x = canvasWidth + this.size;
  }

  draw() {
    ctx.beginPath();
    ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
    ctx.shadowColor = 'rgba(255, 255, 255, 0.45)';
    ctx.shadowBlur = 6;
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }
}

function initParticles() {
  particles.length = 0;
  for (let i = 0; i < PARTICLE_COUNT; i += 1) {
    particles.push(new Particle());
  }
}

function animateParticles(time = 0) {
  if (!ctx) return;
  ctx.clearRect(0, 0, canvasWidth, canvasHeight);
  particles.forEach((particle) => {
    particle.update(time);
    particle.draw();
  });
  requestAnimationFrame(animateParticles);
}

if (canvas && ctx) {
  resizeCanvas();
  initParticles();
  requestAnimationFrame(animateParticles);

  window.addEventListener('resize', () => {
    resizeCanvas();
    initParticles();
  });

  canvas.addEventListener('mousemove', (event) => {
    const rect = canvas.getBoundingClientRect();
    pointer.x = event.clientX - rect.left;
    pointer.y = event.clientY - rect.top;
    pointer.active = true;
  });

  canvas.addEventListener('mouseleave', () => {
    pointer.active = false;
  });
}



