from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional

from flask import Flask, jsonify, request, send_from_directory, render_template
import csv
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import uuid


app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/static',
    template_folder='templates',
)

# Configuración de seguridad
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-key-por-defecto-cambiar-en-produccion")

CORS(app)

# Limitar tamaño máximo de subida (8 MB por defecto, configurable vía env)
try:
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 8 * 1024 * 1024))
except Exception:
    app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024


# -------------------------------
# Dominio y almacenamiento en memoria
# -------------------------------

Base = declarative_base()


class LibroDB(Base):
    __tablename__ = "libros"
    id = Column(String(64), primary_key=True)
    titulo = Column(String(255), nullable=False)
    autor = Column(String(255), nullable=True)  # Opcional para equipos/PCs
    isbn = Column(String(64), nullable=True)
    editorial = Column(String(255), nullable=True)
    anio_publicacion = Column(Integer, nullable=True)
    categoria = Column(String(128), nullable=True)
    subcategoria = Column(String(128), nullable=True)
    descripcion = Column(Text, nullable=True)
    estado_disponibilidad = Column(String(64), nullable=True)
    estado_elemento = Column(String(64), nullable=True)
    stock = Column(Integer, default=0)
    cantidad_disponible = Column(Integer, default=0)
    cantidad_prestado = Column(Integer, default=0)
    imagen = Column(String(512), nullable=True)
    codigo_inventario = Column(String(128), nullable=True)  # Para equipos: ej. Portátil A1
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)


class PrestamoDB(Base):
    __tablename__ = "prestamos"
    id = Column(String(64), primary_key=True)
    id_elemento = Column(String(64), nullable=False)
    id_usuario = Column(String(128), nullable=True)  # requerido para equipos, opcional para libros
    fecha_prestamo = Column(DateTime, nullable=False)
    fecha_devolucion = Column(DateTime, nullable=True)
    observaciones = Column(Text, nullable=True)
    estado = Column(String(32), nullable=False)  # pendiente, aprobado, rechazado, devuelto
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)


class UserDB(Base):
    __tablename__ = "usuarios"
    id = Column(String(64), primary_key=True)
    nombre = Column(String(255), nullable=False)
    documento = Column(String(64), nullable=False)
    correo = Column(String(255), nullable=True)
    username = Column(String(64), nullable=False, unique=True)
    password = Column(String(255), nullable=False)  # ahora hasheado
    role = Column(String(32), nullable=False, default='user')  # user/admin
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)


class MensajeDB(Base):
    __tablename__ = "mensajes"
    id = Column(String(64), primary_key=True)
    id_remitente = Column(String(64), nullable=False)  # ID usuario que envía
    id_destinatario = Column(String(64), nullable=False)  # 'admin' o ID usuario
    asunto = Column(String(255), nullable=True)
    contenido = Column(Text, nullable=False)
    leido = Column(Integer, nullable=False, default=0)  # 0=no leído, 1=leído
    relacionado_con = Column(String(64), nullable=True)  # ID préstamo, elemento, etc.
    tipo = Column(String(32), nullable=True)  # 'prestamo', 'equipo', 'consulta', 'chat'
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)


class WaitlistDB(Base):
    __tablename__ = "waitlist"
    id = Column(String(64), primary_key=True)
    id_elemento = Column(String(64), nullable=False)
    id_usuario = Column(String(64), nullable=True)
    contacto = Column(String(255), nullable=True)  # correo o documento
    estado = Column(String(32), nullable=False)  # pendiente, notificado
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)


class FavoritoDB(Base):
    __tablename__ = "favoritos"
    id = Column(String(64), primary_key=True)
    id_usuario = Column(String(64), nullable=False)
    id_elemento = Column(String(64), nullable=False)
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)


class SancionTipoDB(Base):
    __tablename__ = "sancion_tipo"
    id = Column(String(64), primary_key=True)
    codigo = Column(String(64), nullable=False, unique=True)  # RB1: obligatorio, único, sin espacios
    descripcion = Column(String(120), nullable=False)  # RB2: obligatoria, longitud 5-120
    usuario_creacion = Column(String(64), nullable=True)  # Auditoría
    creado_en = Column(DateTime, nullable=False)  # Auditoría
    actualizado_en = Column(DateTime, nullable=False)  # Auditoría


class LibroHistorialDB(Base):
    """Tabla de historial para mantener trazabilidad de libros eliminados"""
    __tablename__ = "libro_historial"
    id = Column(String(64), primary_key=True)
    id_libro_original = Column(String(64), nullable=False)  # ID original del libro eliminado
    titulo = Column(String(255), nullable=False)
    autor = Column(String(255), nullable=True)
    isbn = Column(String(64), nullable=True)
    codigo_inventario = Column(String(128), nullable=True)
    categoria = Column(String(128), nullable=True)
    motivo_eliminacion = Column(String(255), nullable=True)  # Razón de la eliminación
    datos_completos = Column(Text, nullable=True)  # JSON con todos los datos del libro
    usuario_eliminador = Column(String(64), nullable=True)  # Quién eliminó
    fecha_eliminacion = Column(DateTime, nullable=False)
    # Relaciones preservadas (solo para referencia histórica)
    prestamos_relacionados = Column(Integer, default=0)  # Cantidad de préstamos que tenía
    favoritos_relacionados = Column(Integer, default=0)  # Cantidad de favoritos que tenía


# Configurar ruta de base de datos (absoluta para producción)
db_path = os.environ.get('DATABASE_URL', 'sqlite:///bibliosena.db')
# Render a veces usa postgres:// en lugar de postgresql://
if db_path.startswith('postgres://'):
    db_path = db_path.replace('postgres://', 'postgresql://', 1)
# Si DATABASE_URL es una URL PostgreSQL de Render, usar directamente; si no, usar SQLite
if db_path.startswith('postgresql://'):
    # PostgreSQL en producción (Render)
    engine = create_engine(db_path, echo=False, future=True, pool_pre_ping=True)
else:
    # SQLite en desarrollo local
    if not db_path.startswith('sqlite:///'):
        db_path = f'sqlite:///{os.path.join(os.path.dirname(__file__), "bibliosena.db")}'
    engine = create_engine(db_path, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


def now_iso() -> str:
    return datetime.utcnow().isoformat() + 'Z'


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Intentar cargar una fuente TrueType común; si falla, usar la fuente por defecto."""
    candidate_paths = [
        "arialbd.ttf" if bold else "arial.ttf",
        os.path.join(os.environ.get("WINDIR", ""), "Fonts", "arialbd.ttf" if bold else "arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text_for_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    """Dividir texto en líneas que se ajusten al ancho máximo."""
    if not text:
        return []
    lines: List[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current_line = words[0]
        for word in words[1:]:
            candidate = f"{current_line} {word}"
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = candidate
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines


def _select_palette(seed_text: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    palettes = [
        ((78, 84, 200), (126, 214, 223), (255, 255, 255)),
        ((118, 75, 162), (236, 132, 209), (255, 230, 255)),
        ((2, 170, 176), (0, 205, 172), (255, 255, 255)),
        ((255, 140, 66), (255, 210, 128), (40, 40, 40)),
        ((77, 160, 176), (211, 236, 221), (255, 255, 255)),
        ((25, 118, 210), (187, 222, 251), (255, 255, 255)),
    ]
    if not seed_text:
        return palettes[0]
    seed = sum(ord(c) for c in seed_text)
    return palettes[seed % len(palettes)]


def _create_gradient_background(width: int, height: int, colors: tuple[tuple[int, int, int], tuple[int, int, int]]) -> Image.Image:
    base = Image.new("RGB", (1, height))
    top, bottom = colors
    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
        g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
        b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
        base.putpixel((0, y), (r, g, b))
    resample = getattr(Image, "Resampling", Image)
    return base.resize((width, height), resample.BICUBIC)


def _add_overlay_elements(image: Image.Image, accent: tuple[int, int, int], seed: int) -> Image.Image:
    width, height = image.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    accent_soft = (*accent, 120)
    accent_bold = (*accent, 180)

    # Elementos geométricos principales
    draw.ellipse(
        (-width * 0.2, height * 0.1, width * 0.6, height * 0.9),
        fill=accent_soft,
    )
    draw.rounded_rectangle(
        (width * 0.35, height * 0.05, width * 1.05, height * 0.55),
        radius=120,
        fill=accent_bold,
    )

    # Líneas diagonales translúcidas
    line_color = (*accent, 90)
    step = 40
    for offset in range(-height, width, step):
        draw.line(
            [(offset, 0), (offset + height, height)],
            fill=line_color,
            width=3,
        )

    # Textura suave con ruido
    noise = Image.effect_noise((width, height), 8).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(radius=1.5))
    noise_colored = Image.merge(
        "RGBA",
        (
            noise,
            noise,
            noise,
            Image.new("L", (width, height), 30),
        ),
    )

    composed = Image.alpha_composite(image.convert("RGBA"), overlay)
    composed = Image.alpha_composite(composed, noise_colored)
    return composed.convert("RGB")


def generar_portada(nombre_libro: str, autor: str = "", output_path: Optional[str] = None) -> str:
    """
    Genera una imagen de portada simple con el título y autor del libro.

    Retorna la ruta relativa donde se guarda la imagen (dentro de uploads).
    """
    titulo = (nombre_libro or "").strip() or "Libro sin título"
    autor_txt = (autor or "").strip()

    ancho, alto = 400, 600
    palette_top, palette_bottom, text_color = _select_palette(titulo)
    imagen = _create_gradient_background(ancho, alto, (palette_top, palette_bottom))
    imagen = _add_overlay_elements(imagen, palette_top, sum(ord(c) for c in titulo))

    draw = ImageDraw.Draw(imagen)

    font_titulo = _load_font(32, bold=True)
    font_autor = _load_font(20)

    margen_horizontal = 40
    disponible = ancho - 2 * margen_horizontal
    lineas_titulo = _wrap_text_for_width(draw, titulo, font_titulo, disponible)
    lineas_autor = _wrap_text_for_width(draw, autor_txt, font_autor, disponible) if autor_txt else []

    def _total_height(lines: List[str], font: ImageFont.ImageFont) -> int:
        if not lines:
            return 0
        alturas = []
        for linea in lines:
            bbox = draw.textbbox((0, 0), linea, font=font)
            alturas.append(bbox[3] - bbox[1])
        return sum(alturas) + (len(lines) - 1) * 8

    altura_titulo = _total_height(lineas_titulo, font_titulo)
    altura_autor = _total_height(lineas_autor, font_autor) if lineas_autor else 0
    separacion = 24 if lineas_autor else 0
    altura_total = altura_titulo + separacion + altura_autor

    y_inicio = max(int((alto - altura_total) / 2), margen_horizontal)
    y = y_inicio

    for linea in lineas_titulo:
        bbox = draw.textbbox((0, 0), linea, font=font_titulo)
        ancho_linea = bbox[2] - bbox[0]
        alto_linea = bbox[3] - bbox[1]
        x = (ancho - ancho_linea) / 2
        draw.text((x, y), linea, fill=text_color, font=font_titulo)
        y += alto_linea + 8

    if lineas_autor:
        y += separacion - 8  # ajustar porque el último bucle sumó 8 extra
        for linea in lineas_autor:
            bbox = draw.textbbox((0, 0), linea, font=font_autor)
            ancho_linea = bbox[2] - bbox[0]
            alto_linea = bbox[3] - bbox[1]
            x = (ancho - ancho_linea) / 2
            draw.text((x, y), linea, fill=tuple(min(255, int(c * 0.92)) for c in text_color), font=font_autor)
            y += alto_linea + 6

    # Añadir monograma decorativo
    iniciales = "".join(word[0] for word in titulo.split()[:2]).upper() or "BK"
    monograma_font = _load_font(18, bold=True)
    monograma_text = iniciales[:2]
    monograma_bbox = draw.textbbox((0, 0), monograma_text, font=monograma_font)
    monograma_width = monograma_bbox[2] - monograma_bbox[0]
    monograma_height = monograma_bbox[3] - monograma_bbox[1]
    monograma_padding = 14
    draw.rounded_rectangle(
        (
            ancho - monograma_width - monograma_padding * 2 - 24,
            24,
            ancho - 24,
            24 + monograma_height + monograma_padding * 2,
        ),
        radius=18,
        fill=tuple(min(255, c + 30) for c in palette_top),
    )
    draw.text(
        (
            ancho - monograma_width - monograma_padding - 24,
            24 + monograma_padding - 2,
        ),
        monograma_text,
        fill=(255, 255, 255),
        font=monograma_font,
    )

    uploads_dir = os.path.join(app.root_path, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    if not output_path:
        filename = f"portada_{uuid.uuid4().hex}.jpg"
        output_path = os.path.join(uploads_dir, filename)

    imagen.save(output_path, "JPEG", quality=90, optimize=True, progressive=True)

    return f"uploads/{os.path.basename(output_path)}"


def libro_from_request_db(data: Dict[str, Any]) -> LibroDB:
    now = datetime.utcnow()
    # Detectar si es un equipo/PC o un libro
    categoria = (data.get('categoria', '') or '').lower()
    es_equipo = 'equipo' in categoria or 'informático' in categoria or categoria in ['tablets', 'proyectores', 'otros']
    
    # Para equipos, el autor puede estar vacío o ser None
    # Usar cadena vacía en lugar de None para compatibilidad con BD existentes
    autor = data.get('autor', '').strip() or None
    if es_equipo and not autor:
        # Para equipos, usar cadena vacía como valor por defecto (compatible con NOT NULL)
        autor = ''
    
    # Construir descripción para equipos si no se proporciona
    descripcion = data.get('descripcion', '').strip() or None
    if es_equipo and not descripcion:
        # Construir descripción a partir de campos específicos de equipos
        partes_descripcion = []
        marca = data.get('marca', '').strip()
        modelo = data.get('modelo', '').strip()
        especificaciones = data.get('especificaciones', '').strip()
        numero_serie = data.get('numero_serie', '').strip()
        
        if marca:
            partes_descripcion.append(f"Marca: {marca}")
        if modelo:
            partes_descripcion.append(f"Modelo: {modelo}")
        if especificaciones:
            partes_descripcion.append(f"Especificaciones: {especificaciones}")
        if numero_serie:
            partes_descripcion.append(f"Número de serie: {numero_serie}")
        
        if partes_descripcion:
            descripcion = "\n".join(partes_descripcion)
        else:
            descripcion = "Equipo informático"
    elif es_equipo and descripcion:
        # Si hay descripción manual, agregar información de equipos si está disponible
        info_equipo = []
        marca = data.get('marca', '').strip()
        modelo = data.get('modelo', '').strip()
        especificaciones = data.get('especificaciones', '').strip()
        numero_serie = data.get('numero_serie', '').strip()
        
        if marca and 'Marca:' not in descripcion:
            info_equipo.append(f"Marca: {marca}")
        if modelo and 'Modelo:' not in descripcion:
            info_equipo.append(f"Modelo: {modelo}")
        if especificaciones and 'Especificaciones:' not in descripcion:
            info_equipo.append(f"Especificaciones: {especificaciones}")
        if numero_serie and 'Número de serie:' not in descripcion:
            info_equipo.append(f"Número de serie: {numero_serie}")
        
        if info_equipo:
            descripcion = descripcion + "\n\n" + "\n".join(info_equipo)
    
    # Manejar valores numéricos de forma segura
    try:
        anio_publicacion_val = int(data.get('anio_publicacion', 0) or 0)
        anio_publicacion = anio_publicacion_val if anio_publicacion_val > 0 else None
    except (ValueError, TypeError):
        anio_publicacion = None
    
    try:
        stock_val = int(data.get('stock', 0) or 0)
        stock = stock_val if stock_val >= 0 else 0
    except (ValueError, TypeError):
        stock = 0
    
    try:
        cantidad_disponible_val = int(data.get('cantidad_disponible', 0) or 0)
        cantidad_disponible = cantidad_disponible_val if cantidad_disponible_val >= 0 else 0
    except (ValueError, TypeError):
        cantidad_disponible = stock  # Usar stock como fallback
    
    try:
        cantidad_prestado_val = int(data.get('cantidad_prestado', 0) or 0)
        cantidad_prestado = cantidad_prestado_val if cantidad_prestado_val >= 0 else 0
    except (ValueError, TypeError):
        cantidad_prestado = 0
    
    # Asegurar que descripción no sea None si es equipo
    if es_equipo and not descripcion:
        descripcion = "Equipo informático"
    
    # Asegurar que autor nunca sea None (usar cadena vacía para equipos)
    if autor is None:
        autor = ''
    
    libro = LibroDB(
        id=str(uuid.uuid4()),
        titulo=data.get('titulo', '').strip(),
        autor=autor,  # Cadena vacía para equipos, valor normal para libros
        isbn=(data.get('isbn', '') or '').strip() or None,
        editorial=(data.get('editorial', '') or '').strip() or None,
        anio_publicacion=anio_publicacion,
        categoria=(data.get('categoria', '') or '').strip(),
        subcategoria=(data.get('subcategoria', '') or '').strip() or None,
        descripcion=descripcion,
        estado_disponibilidad=(data.get('estado_disponibilidad', '') or '').strip() or 'Disponible',
        estado_elemento=(data.get('estado_elemento', '') or '').strip() or 'Buen estado',
        stock=stock,
        cantidad_disponible=cantidad_disponible,
        cantidad_prestado=cantidad_prestado,
        imagen=None,
        codigo_inventario=(data.get('codigo_inventario', '') or '').strip() or None,
        creado_en=now,
        actualizado_en=now,
    )

    # Generar portada automática si no se proporcionó imagen
    if not libro.imagen and libro.titulo:
        try:
            libro.imagen = generar_portada(libro.titulo, autor or '')
        except Exception:
            # Mantener imagen en None si falla la generación para no bloquear el flujo
            libro.imagen = None

    return libro


# -------------------------------
# Rutas de HTML estático
# -------------------------------

@app.get('/')
def root_index():
    # Página inicial
    return render_template('login.html')


@app.get('/<path:page>.html')
def render_any_template(page: str):
    # Renderiza cualquier template si existe, p.ej. /principal.html
    template_path = f"{page}.html"
    if os.path.exists(os.path.join(app.template_folder, template_path)):
        return render_template(template_path)
    return ("No encontrado", 404)


@app.get('/micss.css/<path:filename>')
def legacy_css(filename: str):
    # Compatibilidad con enlaces antiguos: micss.css/archivo.css -> static/css/archivo.css
    css_dir = os.path.join(app.static_folder, 'css')
    file_path = os.path.join(css_dir, filename)
    if os.path.exists(file_path):
        return send_from_directory(css_dir, filename)
    return ("No encontrado", 404)


# -------------------------------
# Servir archivos subidos (uploads)
# -------------------------------

@app.get('/uploads/<path:filename>')
def serve_uploads(filename: str):
    # Evitar traversal y nombres maliciosos
    filename_clean = secure_filename(os.path.basename(filename))
    uploads_dir = os.path.join(app.root_path, 'uploads')
    file_path = os.path.join(uploads_dir, filename_clean)
    if os.path.exists(file_path):
        return send_from_directory(uploads_dir, filename_clean)
    return ("No encontrado", 404)


# -------------------------------
# API mock: autenticación muy básica
# -------------------------------

@app.get('/api/usuarios')
def listar_usuarios():
    """Listar todos los usuarios (solo admin)"""
    db = SessionLocal()
    try:
        # En un sistema real, verificar token admin aquí
        users = db.query(UserDB).all()
        return jsonify([
            {
                "id": u.id,
                "nombre": u.nombre,
                "documento": u.documento,
                "correo": getattr(u, 'correo', None),
                "username": u.username,
                "role": u.role,
                "numero_ficha": getattr(u, 'numero_ficha', None),
                "telefono": getattr(u, 'telefono', None),
                "direccion": getattr(u, 'direccion', None),
                "tipo_usuario": getattr(u, 'tipo_usuario', None),
                "tipo_documento": getattr(u, 'tipo_documento', None),
                "creado_en": u.creado_en.isoformat() + 'Z' if u.creado_en else None
            }
            for u in users
        ])
    finally:
        db.close()

@app.get('/api/usuarios/<usuario_id>')
def obtener_usuario(usuario_id: str):
    """Obtener información de un usuario específico"""
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(
            (UserDB.id == usuario_id) | (UserDB.documento == usuario_id) | (UserDB.username == usuario_id)
        ).first()
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify({
            "id": user.id,
            "nombre": user.nombre,
            "documento": user.documento,
            "correo": getattr(user, 'correo', None),
            "username": user.username,
            "role": user.role,
            "numero_ficha": getattr(user, 'numero_ficha', None),
            "telefono": getattr(user, 'telefono', None),
            "direccion": getattr(user, 'direccion', None),
            "tipo_usuario": getattr(user, 'tipo_usuario', None),
            "tipo_documento": getattr(user, 'tipo_documento', None),
            "creado_en": user.creado_en.isoformat() + 'Z' if user.creado_en else None
        })
    finally:
        db.close()

@app.post('/api/usuarios')
def crear_usuario():
    data = request.get_json(silent=True) or request.form.to_dict()
    nombre = data.get('nombre') or ''
    documento = data.get('documento') or ''
    correo = data.get('correo') or ''
    username = data.get('username') or data.get('user') or ''
    password = data.get('password') or ''
    role = data.get('role') or 'user'
    if not (nombre and documento and username and password):
        return jsonify({"ok": False, "error": "Campos requeridos: nombre, documento, username, password"}), 400
    now = datetime.utcnow()
    db = SessionLocal()
    try:
        # Verificar si el username ya existe
        existing = db.query(UserDB).filter(UserDB.username == username).first()
        if existing:
            return jsonify({"ok": False, "error": "El username ya está en uso"}), 400
        u = UserDB(
            id=str(uuid.uuid4()),
            nombre=nombre,
            documento=documento,
            correo=correo,
            username=username,
            password=generate_password_hash(password),  # Hashear contraseña
            role=role,
            creado_en=now,
            actualizado_en=now
        )
        db.add(u)
        db.commit()
        return jsonify({"ok": True, "id": u.id}), 201
    finally:
        db.close()

@app.put('/api/usuarios/<usuario_id>')
@app.patch('/api/usuarios/<usuario_id>')
def actualizar_usuario(usuario_id: str):
    """Actualizar un usuario"""
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(
            (UserDB.id == usuario_id) | (UserDB.documento == usuario_id) | (UserDB.username == usuario_id)
        ).first()
        if not user:
            return jsonify({"ok": False, "error": "Usuario no encontrado"}), 404
        
        data = request.get_json(silent=True) or request.form.to_dict()
        
        # Actualizar campos permitidos
        if 'nombre' in data:
            user.nombre = data['nombre']
        if 'documento' in data:
            user.documento = data['documento']
        if 'correo' in data:
            user.correo = data['correo']
        if 'username' in data:
            # Verificar que el nuevo username no esté en uso
            existing = db.query(UserDB).filter(
                UserDB.username == data['username'],
                UserDB.id != user.id
            ).first()
            if existing:
                return jsonify({"ok": False, "error": "El username ya está en uso"}), 400
            user.username = data['username']
        if 'password' in data and data['password']:
            user.password = generate_password_hash(data['password'])
        if 'role' in data:
            user.role = data['role']
        if 'numero_ficha' in data:
            setattr(user, 'numero_ficha', data['numero_ficha'])
        if 'telefono' in data:
            setattr(user, 'telefono', data['telefono'])
        if 'direccion' in data:
            setattr(user, 'direccion', data['direccion'])
        if 'tipo_usuario' in data:
            setattr(user, 'tipo_usuario', data['tipo_usuario'])
        if 'tipo_documento' in data:
            setattr(user, 'tipo_documento', data['tipo_documento'])
        
        user.actualizado_en = datetime.utcnow()
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

@app.delete('/api/usuarios/<usuario_id>')
def eliminar_usuario(usuario_id: str):
    """Eliminar un usuario"""
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(
            (UserDB.id == usuario_id) | (UserDB.documento == usuario_id) | (UserDB.username == usuario_id)
        ).first()
        if not user:
            return jsonify({"ok": False, "error": "Usuario no encontrado"}), 404
        
        # No permitir eliminar el usuario admin por defecto
        if user.username == 'admin' and user.role == 'admin':
            return jsonify({"ok": False, "error": "No se puede eliminar el administrador principal"}), 400
        
        db.delete(user)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

@app.post('/api/login')
def api_login():
    payload = request.get_json(silent=True) or request.form
    username = (payload or {}).get('user') or (payload or {}).get('username')
    pwd = (payload or {}).get('password')
    db = SessionLocal()
    try:
        # Admin por defecto (crear si no existe con contraseña hasheada)
        if username == 'admin' and pwd == 'admin':
            admin_user = db.query(UserDB).filter(UserDB.username == 'admin').first()
            if not admin_user:
                # Crear admin inicial si no existe
                now = datetime.utcnow()
                admin_user = UserDB(
                    id=str(uuid.uuid4()),
                    nombre='Administrador',
                    documento='00000000',
                    username='admin',
                    password=generate_password_hash('admin'),
                    role='admin',
                    creado_en=now,
                    actualizado_en=now
                )
                db.add(admin_user)
                db.commit()
            return jsonify({"ok": True, "token": "admin-token", "user": {"name": "Administrador", "role": "admin"}})
        
        # Buscar usuario y verificar contraseña hasheada
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if user:
            # Intentar verificar con hash primero, si falla, verificar sin hash (compatibilidad con usuarios antiguos)
            if check_password_hash(user.password, pwd):
                return jsonify({"ok": True, "token": f"user-{user.id}", "user": {"name": user.nombre, "role": user.role, "id": user.id, "documento": user.documento, "correo": user.correo}})
            # Compatibilidad: si la contraseña está en texto plano, actualizar a hash
            elif user.password == pwd:
                user.password = generate_password_hash(pwd)
                db.commit()
                return jsonify({"ok": True, "token": f"user-{user.id}", "user": {"name": user.nombre, "role": user.role, "id": user.id, "documento": user.documento, "correo": user.correo}})
        return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401
    finally:
        db.close()


# -------------------------------
# API CRUD de libros (en memoria)
# -------------------------------

@app.get('/api/libros')
def libros_listar():
    """
    Listar libros. Si hay múltiples copias del mismo libro, agruparlos por código_inventario o título/ISBN.
    IMPORTANTE: Evita duplicados procesando cada registro solo una vez.
    """
    db = SessionLocal()
    try:
        rows = db.query(LibroDB).all()
        
        # Agrupar por código_inventario si existe, sino por título+autor+ISBN único
        libros_agrupados = {}
        ids_procesados = set()  # Para evitar procesar el mismo registro múltiples veces
        
        for r in rows:
            # Si ya fue procesado, saltarlo
            if r.id in ids_procesados:
                continue
            
            # Determinar clave de agrupación
            if r.codigo_inventario and r.codigo_inventario.strip():
                # Agrupar por código_inventario
                clave = f"cod_{r.codigo_inventario.strip()}"
                
                # Buscar TODAS las copias con este código_inventario
                copias_relacionadas = db.query(LibroDB).filter(
                    LibroDB.codigo_inventario == r.codigo_inventario
                ).all()
            else:
                # Agrupar por título+autor+ISBN (libros idénticos)
                titulo_norm = (r.titulo or '').strip()
                autor_norm = (r.autor or '').strip()
                isbn_norm = (r.isbn or '').strip()
                clave = f"tit_{titulo_norm}_{autor_norm}_{isbn_norm}"
                
                # Buscar TODAS las copias con estos datos (que NO tengan código_inventario)
                copias_relacionadas = db.query(LibroDB).filter(
                    LibroDB.titulo == titulo_norm,
                    LibroDB.autor == autor_norm,
                    LibroDB.isbn == isbn_norm,
                    ((LibroDB.codigo_inventario == None) | (LibroDB.codigo_inventario == ''))
                ).all()
            
            # Agrupar todas las copias encontradas
            if copias_relacionadas:
                libro_base = copias_relacionadas[0]  # Usar el primero como base
                
                # Sumar stocks de todas las copias
                stock_total = sum(c.stock or 0 for c in copias_relacionadas)
                cantidad_disponible_total = sum(c.cantidad_disponible or 0 for c in copias_relacionadas)
                cantidad_prestado_total = sum(c.cantidad_prestado or 0 for c in copias_relacionadas)
                
                # Crear entrada agrupada
                libros_agrupados[clave] = {
                    'id': libro_base.id,
                    'titulo': libro_base.titulo,
                    'autor': libro_base.autor,
                    'isbn': libro_base.isbn,
                    'editorial': libro_base.editorial,
                    'anio_publicacion': libro_base.anio_publicacion,
                    'categoria': libro_base.categoria,
                    'subcategoria': libro_base.subcategoria,
                    'descripcion': libro_base.descripcion,
                    'estado_disponibilidad': libro_base.estado_disponibilidad,
                    'estado_elemento': libro_base.estado_elemento,
                    'stock': stock_total,
                    'cantidad_disponible': cantidad_disponible_total,
                    'cantidad_prestado': cantidad_prestado_total,
                    'imagen': libro_base.imagen,
                    'codigo_inventario': libro_base.codigo_inventario,
                    'creado_en': libro_base.creado_en.isoformat() + 'Z',
                    'actualizado_en': libro_base.actualizado_en.isoformat() + 'Z',
                }
                
                # Marcar TODAS las copias como procesadas
                for copia in copias_relacionadas:
                    ids_procesados.add(copia.id)
        
        items = list(libros_agrupados.values())
        return jsonify(items)
    finally:
        db.close()


@app.post('/api/libros')
def libros_crear():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    
    # Debug: mostrar datos recibidos
    print("=" * 60)
    print("DATOS RECIBIDOS EN /api/libros:")
    print(f"Tipo de request: {type(request.form)}")
    print(f"Datos recibidos: {data}")
    print(f"Campos en request.form: {list(request.form.keys()) if request.form else 'No hay form'}")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Validar campos requeridos
        titulo = data.get('titulo', '').strip()
        if not titulo:
            return jsonify({"ok": False, "error": "El título es requerido"}), 400
        
        # Validar categoría
        categoria = data.get('categoria', '').strip()
        if not categoria:
            return jsonify({"ok": False, "error": "La categoría es requerida"}), 400
        
        # Validar que para libros se tenga autor
        es_equipo = 'equipo' in categoria.lower() or 'informático' in categoria.lower()
        if not es_equipo:
            autor = data.get('autor', '').strip()
            if not autor:
                return jsonify({"ok": False, "error": "El autor es requerido para libros"}), 400
        # Para equipos, asegurar que autor sea cadena vacía si no está presente
        elif es_equipo:
            autor = data.get('autor', '').strip()
            if not autor:
                data['autor'] = ''  # Asegurar cadena vacía para equipos
        
        libro = libro_from_request_db(data)
        
        # Asegurar que todos los campos requeridos por la BD tengan valores
        if not libro.titulo:
            return jsonify({"ok": False, "error": "El título es requerido"}), 400
        if not libro.categoria:
            return jsonify({"ok": False, "error": "La categoría es requerida"}), 400
        if libro.stock is None:
            libro.stock = 0
        if libro.cantidad_disponible is None:
            libro.cantidad_disponible = libro.stock or 0
        if libro.cantidad_prestado is None:
            libro.cantidad_prestado = 0
        if not libro.estado_disponibilidad:
            libro.estado_disponibilidad = 'Disponible'
        if not libro.estado_elemento:
            libro.estado_elemento = 'Buen estado'
        if not libro.descripcion:
            libro.descripcion = 'Sin descripción'
        
        file = request.files.get('imagen') if 'imagen' in request.files else None
        if file and file.filename:
            uploads_dir = os.path.join(app.root_path, 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            filename = secure_filename(file.filename)
            stored_name = f"{libro.id}_{filename}"
            save_path = os.path.join(uploads_dir, stored_name)
            file.save(save_path)
            # Guardar ruta relativa que las plantillas esperan: 'uploads/<filename>'
            libro.imagen = f"uploads/{stored_name}"
        
        print(f"Libro a crear: titulo={libro.titulo}, categoria={libro.categoria}, autor={libro.autor}")
        db.add(libro)
        db.commit()
        return jsonify({"ok": True, "id": libro.id}), 201
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        import traceback
        print(f"Error al crear elemento: {error_msg}")
        print(traceback.format_exc())
        # Mensajes de error más amigables
        if "NOT NULL constraint" in error_msg or "null value" in error_msg.lower():
            return jsonify({"ok": False, "error": f"Faltan campos requeridos: {error_msg}"}), 400
        return jsonify({"ok": False, "error": f"Error al crear elemento: {error_msg}"}), 500
    finally:
        db.close()


@app.get('/api/libros/<libro_id>')
def libros_obtener(libro_id: str):
    db = SessionLocal()
    try:
        r = db.get(LibroDB, libro_id)
        if not r:
            return ("No encontrado", 404)

        # Calcular información agregada para todas las copias relacionadas
        if r.codigo_inventario and r.codigo_inventario.strip():
            copias_relacionadas = db.query(LibroDB).filter(
                LibroDB.codigo_inventario == r.codigo_inventario
            ).all()
        else:
            titulo_norm = (r.titulo or '').strip()
            autor_norm = (r.autor or '').strip()
            isbn_norm = (r.isbn or '').strip()
            copias_relacionadas = db.query(LibroDB).filter(
                LibroDB.titulo == titulo_norm,
                LibroDB.autor == autor_norm,
                LibroDB.isbn == isbn_norm,
                ((LibroDB.codigo_inventario == None) | (LibroDB.codigo_inventario == ''))
            ).all()

        if copias_relacionadas:
            stock_total = sum(c.stock or 0 for c in copias_relacionadas)
            cantidad_disponible_total = sum(c.cantidad_disponible or 0 for c in copias_relacionadas)
            cantidad_prestado_total = sum(c.cantidad_prestado or 0 for c in copias_relacionadas)
        else:
            stock_total = r.stock or 0
            cantidad_disponible_total = r.cantidad_disponible or 0
            cantidad_prestado_total = r.cantidad_prestado or 0

        item = {
            **{k: getattr(r, k) for k in [
                'id',
                'titulo',
                'autor',
                'isbn',
                'editorial',
                'anio_publicacion',
                'categoria',
                'subcategoria',
                'descripcion',
                'estado_disponibilidad',
                'estado_elemento',
                'stock',
                'cantidad_disponible',
                'cantidad_prestado',
                'imagen',
                'codigo_inventario',
            ]},
            'creado_en': r.creado_en.isoformat()+'Z',
            'actualizado_en': r.actualizado_en.isoformat()+'Z',
            'stock_total': stock_total,
            'cantidad_disponible_total': cantidad_disponible_total,
            'cantidad_prestado_total': cantidad_prestado_total,
            'copias_relacionadas': [c.id for c in copias_relacionadas] if copias_relacionadas else [r.id],
        }
        return jsonify(item)
    finally:
        db.close()


# -------------------------------
# Préstamos
# -------------------------------

@app.post('/prestamos')
def crear_prestamo():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    id_elemento = data.get('id_elemento')
    id_usuario_raw = data.get('id_usuario')  # Puede ser ID, documento o username
    fecha_prestamo_str = data.get('fecha_prestamo')
    fecha_devolucion_str = data.get('fecha_devolucion')
    observaciones = data.get('observaciones')

    if not id_elemento:
        return jsonify({"ok": False, "error": "id_elemento es requerido"}), 400

    db = SessionLocal()
    try:
        # Buscar elemento por ID exacto primero
        elemento = db.get(LibroDB, id_elemento)
        
        # Si no se encuentra por ID exacto, buscar por título o código de inventario
        if not elemento:
            elemento = db.query(LibroDB).filter(
                (LibroDB.titulo == id_elemento) | 
                (LibroDB.codigo_inventario == id_elemento) |
                (LibroDB.id.like(f'%{id_elemento}%'))
            ).first()
        
        if not elemento:
            return jsonify({"ok": False, "error": f"Elemento no encontrado con ID: {id_elemento}"}), 404

        # IMPORTANTE: Usar el ID real del elemento encontrado, no el que vino del formulario
        id_elemento_real = elemento.id

        # Resolver ID real del usuario si se proporciona documento/username
        id_usuario_final = None
        if id_usuario_raw:
            # Buscar usuario por ID, documento o username
            user_match = db.query(UserDB).filter(
                (UserDB.id == id_usuario_raw) | 
                (UserDB.documento == id_usuario_raw) | 
                (UserDB.username == id_usuario_raw)
            ).first()
            if user_match:
                id_usuario_final = user_match.id  # Usar ID real del usuario
            else:
                id_usuario_final = id_usuario_raw  # Si no se encuentra, usar el valor tal cual

        # Regla de negocio: si no es categoría 'Libros', se exige documento/usuario
        categoria = (elemento.categoria or '').strip().lower()
        es_libro = categoria == 'libros'
        if not es_libro and not id_usuario_final:
            return jsonify({"ok": False, "error": "id_usuario es requerido para préstamos de equipos"}), 400

        # Validar disponibilidad; si no hay, crear espera
        if (elemento.cantidad_disponible or 0) <= 0:
            # Crear entrada en waitlist si el cliente lo solicita
            contacto = data.get('contacto') or id_usuario_final
            noww = datetime.utcnow()
            w = WaitlistDB(id=str(uuid.uuid4()), id_elemento=id_elemento_real, id_usuario=id_usuario_final, contacto=contacto, estado='pendiente', creado_en=noww, actualizado_en=noww)
            db.add(w)
            db.commit()
            return jsonify({"ok": False, "error": "Elemento no disponible. Te agregamos a la lista de espera.", "waitlist_id": w.id}), 202

        # Parse de fechas
        try:
            fecha_prestamo = datetime.fromisoformat(fecha_prestamo_str) if fecha_prestamo_str else datetime.utcnow()
        except Exception:
            fecha_prestamo = datetime.utcnow()
        try:
            fecha_devolucion = datetime.fromisoformat(fecha_devolucion_str) if fecha_devolucion_str else None
        except Exception:
            fecha_devolucion = None

        now = datetime.utcnow()
        prestamo = PrestamoDB(
            id=str(uuid.uuid4()),
            id_elemento=id_elemento_real,  # Usar ID real del elemento, no el del formulario
            id_usuario=id_usuario_final,  # Usar ID real del usuario
            fecha_prestamo=fecha_prestamo,
            fecha_devolucion=fecha_devolucion,
            observaciones=observaciones,
            estado='pendiente',
            creado_en=now,
            actualizado_en=now,
        )

        db.add(prestamo)
        db.commit()
        return jsonify({"ok": True, "id": prestamo.id}), 201
    finally:
        db.close()

@app.get('/prestamos')
def listar_prestamos():
    estado = request.args.get('estado')
    usuario = request.args.get('usuario')  # ID, documento o username del usuario
    prestamo_id = request.args.get('id')  # Búsqueda por ID de préstamo
    db = SessionLocal()
    try:
        q = db.query(PrestamoDB)
        
        # Búsqueda por ID de préstamo
        if prestamo_id:
            q = q.filter(PrestamoDB.id == prestamo_id)
        
        if estado:
            q = q.filter(PrestamoDB.estado == estado)
            
        if usuario:
            # Filtrar por usuario (buscar por ID, documento o username)
            # Primero intentar encontrar el usuario
            user_match = db.query(UserDB).filter(
                (UserDB.id == usuario) | (UserDB.documento == usuario) | (UserDB.username == usuario)
            ).first()
            if user_match:
                # Usar el ID encontrado - BUSCAR POR ID O DOCUMENTO EN EL PRÉSTAMO
                q = q.filter(
                    (PrestamoDB.id_usuario == user_match.id) | 
                    (PrestamoDB.id_usuario == user_match.documento)
                )
            else:
                # Si no se encuentra, buscar directamente por ID o documento en préstamos
                q = q.filter(
                    (PrestamoDB.id_usuario == usuario) | 
                    (PrestamoDB.id_usuario.like(f'%{usuario}%'))
                )
        
        rows = q.order_by(PrestamoDB.creado_en.desc()).all()
        
        # Enriquecer con datos de usuario y elemento
        items = []
        for r in rows:
            # Obtener datos del usuario
            usuario_data = None
            if r.id_usuario:
                user = db.query(UserDB).filter(
                    (UserDB.id == r.id_usuario) | (UserDB.documento == r.id_usuario) | (UserDB.username == r.id_usuario)
                ).first()
                if user:
                    usuario_data = {
                        'id': user.id,
                        'nombre': user.nombre,
                        'documento': user.documento,
                        'numero_ficha': getattr(user, 'numero_ficha', None),
                        'correo': getattr(user, 'correo', None),
                    }
            
            # Obtener datos del elemento
            elemento_data = None
            elemento = db.get(LibroDB, r.id_elemento)
            if elemento:
                elemento_data = {
                    'titulo': elemento.titulo,
                    'autor': elemento.autor,
                    'categoria': elemento.categoria,
                    'codigo_inventario': elemento.codigo_inventario,
                }
            
            items.append({
                'id': r.id,
                'id_elemento': r.id_elemento,
                'id_usuario': r.id_usuario,
                'fecha_prestamo': r.fecha_prestamo.isoformat()+'Z',
                'fecha_devolucion': r.fecha_devolucion.isoformat()+'Z' if r.fecha_devolucion else None,
                'observaciones': r.observaciones,
                'estado': r.estado,
                'creado_en': r.creado_en.isoformat()+'Z',
                'actualizado_en': r.actualizado_en.isoformat()+'Z',
                'usuario': usuario_data,
                'elemento': elemento_data,
            })
        
        return jsonify(items)
    finally:
        db.close()

@app.post('/prestamos/manual')
def crear_prestamo_manual():
    data = request.get_json(silent=True) or request.form.to_dict()
    id_elemento = data.get('id_elemento')
    documento = data.get('documento')
    observaciones = data.get('observaciones')
    if not (id_elemento and documento):
        return jsonify({"ok": False, "error": "id_elemento y documento son requeridos"}), 400
    db = SessionLocal()
    try:
        elemento = db.get(LibroDB, id_elemento)
        if not elemento:
            return jsonify({"ok": False, "error": "Elemento no encontrado"}), 404
        if (elemento.cantidad_disponible or 0) <= 0:
            return jsonify({"ok": False, "error": "Elemento no disponible"}), 409
        now = datetime.utcnow()
        p = PrestamoDB(id=str(uuid.uuid4()), id_elemento=id_elemento, id_usuario=documento, fecha_prestamo=now, fecha_devolucion=None, observaciones=observaciones, estado='aprobado', creado_en=now, actualizado_en=now)
        elemento.cantidad_disponible = int((elemento.cantidad_disponible or 0) - 1)
        elemento.cantidad_prestado = int((elemento.cantidad_prestado or 0) + 1)
        elemento.estado_disponibilidad = 'Prestado' if elemento.cantidad_disponible == 0 else 'Disponible'
        elemento.actualizado_en = now
        db.add(p)
        db.commit()
        return jsonify({"ok": True, "id": p.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"Error al crear préstamo manual: {str(e)}"}), 500
    finally:
        db.close()

@app.put('/prestamos/<prestamo_id>/aprobar')
def aprobar_prestamo(prestamo_id: str):
    db = SessionLocal()
    try:
        p = db.get(PrestamoDB, prestamo_id)
        if not p:
            return ("No encontrado", 404)
        if p.estado != 'pendiente':
            return jsonify({"ok": False, "error": "Solo se pueden aprobar préstamos pendientes"}), 400
        elemento = db.get(LibroDB, p.id_elemento)
        if not elemento:
            return jsonify({"ok": False, "error": "Elemento no encontrado"}), 404
        categoria = (elemento.categoria or '').strip().lower()
        es_libro = categoria == 'libros'
        if not es_libro and not p.id_usuario:
            return jsonify({"ok": False, "error": "id_usuario es requerido para equipos"}), 400
        if (elemento.cantidad_disponible or 0) <= 0:
            return jsonify({"ok": False, "error": "Elemento no disponible"}), 409
        # Aplicar impacto de stock al aprobar
        elemento.cantidad_disponible = int((elemento.cantidad_disponible or 0) - 1)
        elemento.cantidad_prestado = int((elemento.cantidad_prestado or 0) + 1)
        elemento.estado_disponibilidad = 'Prestado' if elemento.cantidad_disponible == 0 else 'Disponible'
        elemento.actualizado_en = datetime.utcnow()
        p.estado = 'aprobado'
        p.actualizado_en = datetime.utcnow()
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"Error al aprobar préstamo: {str(e)}"}), 500
    finally:
        db.close()

@app.put('/prestamos/<prestamo_id>/rechazar')
def rechazar_prestamo(prestamo_id: str):
    db = SessionLocal()
    try:
        p = db.get(PrestamoDB, prestamo_id)
        if not p:
            return ("No encontrado", 404)
        if p.estado != 'pendiente':
            return jsonify({"ok": False, "error": "Solo se pueden rechazar préstamos pendientes"}), 400
        p.estado = 'rechazado'
        p.actualizado_en = datetime.utcnow()
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

@app.put('/prestamos/<prestamo_id>/devolver')
def devolver_prestamo(prestamo_id: str):
    db = SessionLocal()
    try:
        p = db.get(PrestamoDB, prestamo_id)
        if not p:
            return ("No encontrado", 404)
        if p.estado != 'aprobado':
            return jsonify({"ok": False, "error": "Solo se pueden devolver préstamos aprobados"}), 400
        elemento = db.get(LibroDB, p.id_elemento)
        if not elemento:
            return jsonify({"ok": False, "error": "Elemento no encontrado"}), 404
        # Incrementar cantidad disponible y decrementar cantidad prestado
        elemento.cantidad_disponible = int((elemento.cantidad_disponible or 0) + 1)
        elemento.cantidad_prestado = int((elemento.cantidad_prestado or 0) - 1) if (elemento.cantidad_prestado or 0) > 0 else 0
        # Actualizar estado de disponibilidad basado en stock disponible
        elemento.estado_disponibilidad = 'Disponible' if (elemento.cantidad_disponible or 0) > 0 else 'Agotado'
        elemento.actualizado_en = datetime.utcnow()
        p.estado = 'devuelto'
        p.fecha_devolucion = datetime.utcnow()
        p.actualizado_en = datetime.utcnow()
        db.commit()
        # Notificar lista de espera (marcar primer pendiente como notificado)
        try:
            w = db.query(WaitlistDB).filter(WaitlistDB.id_elemento == p.id_elemento, WaitlistDB.estado == 'pendiente').order_by(WaitlistDB.creado_en.asc()).first()
            if w:
                w.estado = 'notificado'
                w.actualizado_en = datetime.utcnow()
                db.commit()
        except Exception:
            pass  # Si hay error al notificar waitlist, no es crítico
        return jsonify({"ok": True})
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"Error al devolver préstamo: {str(e)}"}), 500
    finally:
        db.close()

# Inventario resumen y espera
@app.get('/inventario/resumen')
def inventario_resumen():
    db = SessionLocal()
    try:
        rows = db.query(LibroDB).all()
        resumen: Dict[str, Dict[str, int]] = {}
        for r in rows:
            cat = (r.categoria or 'Sin categoría')
            if cat not in resumen:
                resumen[cat] = { 'total': 0, 'disponible': 0, 'prestado': 0 }
            resumen[cat]['total'] += (r.stock or 0)
            resumen[cat]['disponible'] += (r.cantidad_disponible or 0)
            resumen[cat]['prestado'] += (r.cantidad_prestado or 0)
        return jsonify(resumen)
    finally:
        db.close()

@app.get('/espera')
def listar_espera():
    db = SessionLocal()
    try:
        rows = db.query(WaitlistDB).all()
        return jsonify([
            { 'id': w.id, 'id_elemento': w.id_elemento, 'id_usuario': w.id_usuario, 'contacto': w.contacto, 'estado': w.estado, 'creado_en': w.creado_en.isoformat()+'Z' }
            for w in rows
        ])
    finally:
        db.close()

@app.post('/import/csv')
def import_csv():
    """Importación masiva desde CSV (exportable de Excel).
    Soporta dos formatos:
    - Formato propio (cabeceras en minúsculas: titulo, autor, isbn, editorial, anio_publicacion, categoria, subcategoria, descripcion, stock, cantidad_disponible, codigo_inventario)
    - Formato Aleph (cabeceras en español con ';' como separador: ISBN;Autor;Título;Subtítulo;Edición;Lugar;Editor;Fecha;Descripción;Adquisición;Código de barras;...)
    """
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "Archivo CSV requerido (campo 'file')"}), 400
    file = request.files['file']
    db = SessionLocal()
    creados = 0
    actualizados = 0
    try:
        # Leer primeras bytes para detectar delimitador y encoding probable
        raw = file.read()
        # Intentar latin-1 primero por caracteres acentuados del archivo proporcionado
        text = None
        for enc in ['latin-1', 'utf-8']:
            try:
                text = raw.decode(enc)
                break
            except Exception:
                continue
        if text is None:
            return jsonify({"ok": False, "error": "No se pudo decodificar el archivo (utf-8/latin-1)"}), 400

        # Determinar delimitador: si hay muchos ';' en la cabecera, usar ';'
        first_line = text.splitlines()[0] if text.splitlines() else ''
        delimiter = ';' if first_line.count(';') > first_line.count(',') else ','

        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)

        def norm(s: str) -> str:
            return (s or '').strip()

        # Mapeo de cabeceras Aleph -> campos internos
        aleph_map = {
            'isbn': 'isbn',
            'autor': 'autor',
            'título': 'titulo',
            'titulo': 'titulo',
            'subtítulo': 'subtitulo',
            'subtitulo': 'subtitulo',
            'editor': 'editorial',
            'fecha': 'anio_publicacion',
            'descripción': 'descripcion',
            'descripcion': 'descripcion',
            'código de barras': 'codigo_barras',
            'codigo de barras': 'codigo_barras',
        }

        for row in reader:
            # Normalizar claves
            keys = { (k or '').strip().lower(): v for k, v in row.items() }

            if any(k in keys for k in aleph_map.keys()):
                # Formato Aleph
                data: Dict[str, Any] = {}
                for k_src, k_dst in aleph_map.items():
                    if k_src in keys:
                        data[k_dst] = norm(keys.get(k_src))
                # Construir título con subtítulo si existe
                titulo = data.get('titulo') or ''
                subt = data.get('subtitulo') or ''
                if subt:
                    titulo = f"{titulo}: {subt}"
                autor = data.get('autor') or ''
                editorial = data.get('editorial') or ''
                isbn = data.get('isbn') or ''
                # Año desde 'Fecha' (puede venir como '2012' o similar)
                anio = 0
                try:
                    anio = int(''.join([c for c in (data.get('anio_publicacion') or '') if c.isdigit()])[:4] or 0)
                except Exception:
                    anio = 0
                descripcion = data.get('descripcion') or ''
                # Para Aleph, cada fila suele representar un ejemplar (código de barras). Agrupamos por ISBN+titulo+editorial
                q = db.query(LibroDB)
                if isbn:
                    q = q.filter(LibroDB.isbn == isbn)
                q = q.filter(LibroDB.titulo == (titulo or ''), LibroDB.editorial == (editorial or ''))
                existente = q.first()
                now = datetime.utcnow()
                if existente:
                    existente.stock = int((existente.stock or 0) + 1)
                    existente.cantidad_disponible = int((existente.cantidad_disponible or 0) + 1)
                    existente.actualizado_en = now
                    if not existente.imagen:
                        try:
                            existente.imagen = generar_portada(titulo, autor)
                        except Exception:
                            pass
                    actualizados += 1
                else:
                    nuevo = LibroDB(
                        id=str(uuid.uuid4()),
                        titulo=titulo,
                        autor=autor,
                        isbn=isbn,
                        editorial=editorial,
                        anio_publicacion=anio,
                        categoria='Libros',
                        subcategoria=None,
                        descripcion=descripcion,
                        estado_disponibilidad='Disponible',
                        estado_elemento='Buen estado',
                        stock=1,
                        cantidad_disponible=1,
                        cantidad_prestado=0,
                        imagen=None,
                        codigo_inventario=None,
                        creado_en=now,
                        actualizado_en=now,
                    )
                    try:
                        nuevo.imagen = generar_portada(titulo, autor)
                    except Exception:
                        nuevo.imagen = None
                    db.add(nuevo)
                    creados += 1
            else:
                # Formato propio (minúsculas)
                data = {k: norm(v) for k, v in keys.items()}
                item = libro_from_request_db(data)
                try:
                    item.stock = int(data.get('stock') or 0)
                    item.cantidad_disponible = int(data.get('cantidad_disponible') or item.stock)
                except Exception:
                    item.stock = item.stock or 0
                    item.cantidad_disponible = item.cantidad_disponible or 0
                db.add(item)
                creados += 1

        db.commit()
        return jsonify({"ok": True, "creados": creados, "actualizados": actualizados})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        db.close()

@app.put('/espera/<espera_id>/notificar')
def marcar_notificado(espera_id: str):
    db = SessionLocal()
    try:
        w = db.get(WaitlistDB, espera_id)
        if not w:
            return ("No encontrado", 404)
        w.estado = 'notificado'
        w.actualizado_en = datetime.utcnow()
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@app.get('/api/favoritos')
def listar_favoritos_api():
    """Listar favoritos de un usuario. Parámetro: usuario (id) o Authorization header 'user-<id>'"""
    usuario = request.args.get('usuario')
    auth = request.headers.get('Authorization') or request.headers.get('authorization')
    if not usuario and auth:
        # soportar token en formato 'user-<id>' o 'Bearer user-<id>'
        token = auth.split()[-1]
        if token.startswith('user-'):
            usuario = token.replace('user-', '')
    if not usuario:
        return jsonify([])
    db = SessionLocal()
    try:
        rows = db.query(FavoritoDB).filter(FavoritoDB.id_usuario == usuario).all()
        items = [ { 'id': r.id, 'id_usuario': r.id_usuario, 'id_elemento': r.id_elemento, 'creado_en': r.creado_en.isoformat()+'Z' } for r in rows ]
        return jsonify(items)
    finally:
        db.close()


@app.post('/api/favoritos')
def crear_favorito_api():
    data = request.get_json(silent=True) or request.form.to_dict()
    id_elemento = data.get('id_elemento')
    id_usuario = data.get('id_usuario')
    # intentar obtener usuario desde Authorization si no viene en body
    if not id_usuario:
        auth = request.headers.get('Authorization') or request.headers.get('authorization')
        if auth:
            token = auth.split()[-1]
            if token.startswith('user-'):
                id_usuario = token.replace('user-', '')
    if not (id_elemento and id_usuario):
        return jsonify({'ok': False, 'error': 'id_elemento e id_usuario son requeridos'}), 400
    db = SessionLocal()
    try:
        # evitar duplicados
        exists = db.query(FavoritoDB).filter(FavoritoDB.id_usuario == id_usuario, FavoritoDB.id_elemento == id_elemento).first()
        if exists:
            return jsonify({'ok': True, 'id': exists.id}), 200
        now = datetime.utcnow()
        f = FavoritoDB(id=str(uuid.uuid4()), id_usuario=id_usuario, id_elemento=id_elemento, creado_en=now, actualizado_en=now)
        db.add(f)
        db.commit()
        return jsonify({'ok': True, 'id': f.id}), 201
    finally:
        db.close()


@app.delete('/api/favoritos/<id_elemento>')
def eliminar_favorito_api(id_elemento: str):
    usuario = request.args.get('usuario')
    # intentar obtener usuario desde Authorization
    if not usuario:
        auth = request.headers.get('Authorization') or request.headers.get('authorization')
        if auth:
            token = auth.split()[-1]
            if token.startswith('user-'):
                usuario = token.replace('user-', '')
    if not usuario:
        return jsonify({'ok': False, 'error': 'usuario requerido'}), 400
    db = SessionLocal()
    try:
        f = db.query(FavoritoDB).filter(FavoritoDB.id_usuario == usuario, FavoritoDB.id_elemento == id_elemento).first()
        if not f:
            return ("No encontrado", 404)
        db.delete(f)
        db.commit()
        return ('', 204)
    finally:
        db.close()

@app.put('/api/libros/<libro_id>')
@app.patch('/api/libros/<libro_id>')
def libros_actualizar(libro_id: str):
    db = SessionLocal()
    try:
        r = db.get(LibroDB, libro_id)
        if not r:
            return ("No encontrado", 404)
        data = request.get_json(silent=True) or request.form.to_dict()
        for field in ['titulo','autor','isbn','editorial','anio_publicacion','categoria','subcategoria','descripcion','estado_disponibilidad','estado_elemento','stock','cantidad_disponible','cantidad_prestado']:
            if field in data:
                value = data[field]
                if field in ['anio_publicacion','stock','cantidad_disponible','cantidad_prestado']:
                    try:
                        value = int(value)
                    except Exception:
                        value = 0
                setattr(r, field, value)
        r.actualizado_en = datetime.utcnow()
        db.commit()
        return ("", 204)
    finally:
        db.close()


@app.delete('/api/libros/<libro_id>')
def libros_eliminar(libro_id: str):
    """
    Eliminar libro con trazabilidad.
    Si el libro tiene código_inventario, elimina todas las copias con ese código.
    Si no, busca por título+autor+ISBN y elimina todas las copias relacionadas.
    """
    db = SessionLocal()
    try:
        # Obtener el libro original
        libro_original = db.get(LibroDB, libro_id)
        if not libro_original:
            return jsonify({"ok": False, "error": "Libro no encontrado"}), 404
        
        # Determinar criterio de búsqueda
        codigo_inventario = libro_original.codigo_inventario
        titulo = libro_original.titulo or ''
        autor = libro_original.autor or ''
        isbn = libro_original.isbn or ''
        
        # Buscar TODOS los registros relacionados
        if codigo_inventario:
            # Si tiene código_inventario, buscar todas las copias con ese código
            registros_relacionados = db.query(LibroDB).filter(
                LibroDB.codigo_inventario == codigo_inventario
            ).all()
        else:
            # Si no tiene código, buscar por título+autor+ISBN (libros idénticos)
            registros_relacionados = db.query(LibroDB).filter(
                LibroDB.titulo == titulo,
                LibroDB.autor == autor,
                LibroDB.isbn == isbn
            ).all()
        
        if not registros_relacionados:
            return jsonify({"ok": False, "error": "No se encontraron registros relacionados"}), 404
        
        # Contar relaciones antes de eliminar (para trazabilidad)
        ids_a_eliminar = [r.id for r in registros_relacionados]
        
        # Contar préstamos relacionados
        prestamos_count = db.query(PrestamoDB).filter(
            PrestamoDB.id_elemento.in_(ids_a_eliminar)
        ).count()
        
        # Contar favoritos relacionados
        favoritos_count = db.query(FavoritoDB).filter(
            FavoritoDB.id_elemento.in_(ids_a_eliminar)
        ).count()
        
        # Contar waitlist relacionadas
        waitlist_count = db.query(WaitlistDB).filter(
            WaitlistDB.id_elemento.in_(ids_a_eliminar)
        ).count()
        
        # Crear registro en historial (usar el primer registro como representativo)
        libro_representativo = registros_relacionados[0]
        import json
        datos_completos = {
            'titulo': libro_representativo.titulo,
            'autor': libro_representativo.autor,
            'isbn': libro_representativo.isbn,
            'editorial': libro_representativo.editorial,
            'categoria': libro_representativo.categoria,
            'stock': sum(r.stock or 0 for r in registros_relacionados),
            'cantidad_disponible': sum(r.cantidad_disponible or 0 for r in registros_relacionados),
            'cantidad_prestado': sum(r.cantidad_prestado or 0 for r in registros_relacionados),
            'codigo_inventario': codigo_inventario,
            'total_copias': len(registros_relacionados)
        }
        
        historial = LibroHistorialDB(
            id=str(uuid.uuid4()),
            id_libro_original=libro_id,
            titulo=libro_representativo.titulo,
            autor=libro_representativo.autor,
            isbn=libro_representativo.isbn,
            codigo_inventario=codigo_inventario,
            categoria=libro_representativo.categoria,
            datos_completos=json.dumps(datos_completos),
            prestamos_relacionados=prestamos_count,
            favoritos_relacionados=favoritos_count,
            fecha_eliminacion=datetime.utcnow()
        )
        db.add(historial)
        
        # Eliminar relaciones (opcional: podemos comentar esto si queremos mantener historial completo)
        # Eliminar favoritos
        db.query(FavoritoDB).filter(FavoritoDB.id_elemento.in_(ids_a_eliminar)).delete(synchronize_session=False)
        
        # Eliminar waitlist
        db.query(WaitlistDB).filter(WaitlistDB.id_elemento.in_(ids_a_eliminar)).delete(synchronize_session=False)
        
        # NOTA: NO eliminamos préstamos porque son parte del historial importante
        # Los préstamos permanecen para trazabilidad, aunque el libro ya no exista
        
        # Eliminar TODOS los registros relacionados
        for registro in registros_relacionados:
            db.delete(registro)
        
        db.commit()
        
        return jsonify({
            "ok": True,
            "eliminados": len(registros_relacionados),
            "prestamos_preservados": prestamos_count,
            "mensaje": f"Se eliminaron {len(registros_relacionados)} registro(s) relacionado(s). Historial preservado."
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"Error al eliminar: {str(e)}"}), 500
    finally:
        db.close()


# -------------------------------
# Sistema de Mensajes Bidireccional
# -------------------------------

@app.post('/api/mensajes')
def crear_mensaje():
    """Crear un mensaje entre usuarios o usuario-admin"""
    data = request.get_json(silent=True) or request.form.to_dict()
    id_remitente = data.get('id_remitente')  # ID del usuario que envía
    id_destinatario = data.get('id_destinatario', 'admin')  # 'admin' o ID usuario
    asunto = data.get('asunto', '')
    contenido = data.get('contenido', '')
    relacionado_con = data.get('relacionado_con')
    tipo = data.get('tipo', 'consulta')
    
    if not id_remitente or not contenido:
        return jsonify({"ok": False, "error": "id_remitente y contenido son requeridos"}), 400
    
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        mensaje = MensajeDB(
            id=str(uuid.uuid4()),
            id_remitente=id_remitente,
            id_destinatario=id_destinatario,
            asunto=asunto,
            contenido=contenido,
            leido=0,
            relacionado_con=relacionado_con,
            tipo=tipo,
            creado_en=now,
            actualizado_en=now
        )
        db.add(mensaje)
        db.commit()
        return jsonify({"ok": True, "id": mensaje.id}), 201
    finally:
        db.close()

@app.get('/api/mensajes')
def listar_mensajes():
    """Listar mensajes para un usuario o admin"""
    id_usuario = request.args.get('usuario')  # ID del usuario
    es_admin = request.args.get('admin') == 'true'
    
    db = SessionLocal()
    try:
        q = db.query(MensajeDB)
        if es_admin:
            # Admin ve todos los mensajes donde es destinatario o remitente
            q = q.filter((MensajeDB.id_destinatario == 'admin') | (MensajeDB.id_remitente == 'admin'))
        else:
            # Usuario ve sus mensajes enviados y recibidos
            q = q.filter((MensajeDB.id_remitente == id_usuario) | (MensajeDB.id_destinatario == id_usuario))
        
        rows = q.order_by(MensajeDB.creado_en.desc()).all()
        items = [
            {
                'id': m.id,
                'id_remitente': m.id_remitente,
                'id_destinatario': m.id_destinatario,
                'asunto': m.asunto,
                'contenido': m.contenido,
                'leido': m.leido,
                'relacionado_con': m.relacionado_con,
                'tipo': m.tipo,
                'creado_en': m.creado_en.isoformat() + 'Z'
            }
            for m in rows
        ]
        return jsonify(items)
    finally:
        db.close()

@app.put('/api/mensajes/<mensaje_id>/leer')
def marcar_leido(mensaje_id: str):
    """Marcar un mensaje como leído"""
    db = SessionLocal()
    try:
        m = db.get(MensajeDB, mensaje_id)
        if not m:
            return ("No encontrado", 404)
        m.leido = 1
        m.actualizado_en = datetime.utcnow()
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()

@app.post('/api/mensajes/conectar')
def conectar_usuarios():
    """Admin puede conectar dos usuarios para que chaten entre sí"""
    data = request.get_json(silent=True) or request.form.to_dict()
    id_usuario1_raw = data.get('usuario1')
    id_usuario2_raw = data.get('usuario2')
    mensaje_inicial = data.get('mensaje', 'El administrador te ha conectado para chatear.')
    
    if not id_usuario1_raw or not id_usuario2_raw:
        return jsonify({"ok": False, "error": "usuario1 y usuario2 son requeridos"}), 400
    
    db = SessionLocal()
    try:
        # Buscar usuarios por ID, documento o username
        user1 = db.query(UserDB).filter(
            (UserDB.id == id_usuario1_raw) | 
            (UserDB.documento == id_usuario1_raw) | 
            (UserDB.username == id_usuario1_raw)
        ).first()
        user2 = db.query(UserDB).filter(
            (UserDB.id == id_usuario2_raw) | 
            (UserDB.documento == id_usuario2_raw) | 
            (UserDB.username == id_usuario2_raw)
        ).first()
        
        if not user1:
            return jsonify({"ok": False, "error": f"Usuario 1 no encontrado: {id_usuario1_raw}"}), 404
        if not user2:
            return jsonify({"ok": False, "error": f"Usuario 2 no encontrado: {id_usuario2_raw}"}), 404
        
        id_usuario1 = user1.id
        id_usuario2 = user2.id
        
        now = datetime.utcnow()
        
        # Crear mensaje de conexión del admin a cada usuario
        msg1 = MensajeDB(
            id=str(uuid.uuid4()),
            id_remitente='admin',
            id_destinatario=id_usuario1,
            asunto='Conexión iniciada',
            contenido=f"Has sido conectado con {user2.nombre} (ID: {user2.documento}). {mensaje_inicial}",
            leido=0,
            tipo='chat',
            relacionado_con=id_usuario2,  # Guardar ID del otro usuario conectado
            creado_en=now,
            actualizado_en=now
        )
        msg2 = MensajeDB(
            id=str(uuid.uuid4()),
            id_remitente='admin',
            id_destinatario=id_usuario2,
            asunto='Conexión iniciada',
            contenido=f"Has sido conectado con {user1.nombre} (ID: {user1.documento}). {mensaje_inicial}",
            leido=0,
            tipo='chat',
            relacionado_con=id_usuario1,  # Guardar ID del otro usuario conectado
            creado_en=now,
            actualizado_en=now
        )
        
        # Crear mensajes bidireccionales entre los usuarios para que puedan chatear
        msg3 = MensajeDB(
            id=str(uuid.uuid4()),
            id_remitente=id_usuario1,
            id_destinatario=id_usuario2,
            asunto='Conexión establecida',
            contenido=f"Hola {user2.nombre}, el administrador nos ha conectado. Puedes responderme aquí.",
            leido=0,
            tipo='chat',
            relacionado_con=id_usuario2,
            creado_en=now,
            actualizado_en=now
        )
        msg4 = MensajeDB(
            id=str(uuid.uuid4()),
            id_remitente=id_usuario2,
            id_destinatario=id_usuario1,
            asunto='Conexión establecida',
            contenido=f"Hola {user1.nombre}, el administrador nos ha conectado. Puedes responderme aquí.",
            leido=0,
            tipo='chat',
            relacionado_con=id_usuario1,
            creado_en=now,
            actualizado_en=now
        )
        
        db.add(msg1)
        db.add(msg2)
        db.add(msg3)
        db.add(msg4)
        db.commit()
        return jsonify({"ok": True, "mensaje": f"Usuarios {user1.nombre} y {user2.nombre} conectados. Pueden chatear entre sí ahora."}), 201
    finally:
        db.close()


# -------------------------------
# API CRUD de Tipos de Sanción
# -------------------------------

def validar_sancion_tipo(codigo, descripcion, db, excluir_id=None):
    """
    Validaciones según RB1-RB4:
    RB1: Código obligatorio, único y sin espacios
    RB2: Descripción obligatoria; longitud 5-120
    RB3: Código en mayúsculas recomendado
    RB4: Verificar duplicados antes de insertar
    
    Retorna: (errores, codigo_validado, descripcion_validada)
    """
    errores = []
    
    # RB1: Código obligatorio
    if not codigo or not codigo.strip():
        errores.append("El código es obligatorio")
        return (errores, None, None)
    
    codigo = codigo.strip()
    
    # RB1: Código sin espacios
    if ' ' in codigo:
        errores.append("El código no debe tener espacios")
        return (errores, None, None)
    
    # RB3: Convertir a mayúsculas (recomendado)
    codigo_validado = codigo.upper()
    
    # RB4: Verificar duplicados antes de insertar
    query = db.query(SancionTipoDB).filter(SancionTipoDB.codigo == codigo_validado)
    if excluir_id:
        query = query.filter(SancionTipoDB.id != excluir_id)
    existe = query.first()
    if existe:
        errores.append("El código ya está registrado")
        return (errores, None, None)
    
    # RB2: Descripción obligatoria
    if not descripcion or not descripcion.strip():
        errores.append("La descripción es obligatoria")
        return (errores, None, None)
    
    descripcion_validada = descripcion.strip()
    
    # RB2: Descripción longitud 5-120
    if len(descripcion_validada) < 5:
        errores.append("La descripción debe tener mínimo 5 caracteres")
        return (errores, None, None)
    
    if len(descripcion_validada) > 120:
        errores.append("La descripción debe tener máximo 120 caracteres")
        return (errores, None, None)
    
    return (errores, codigo_validado, descripcion_validada)


@app.get('/api/sancion-tipos')
def sancion_tipos_listar():
    """Listar todos los tipos de sanción"""
    db = SessionLocal()
    try:
        tipos = db.query(SancionTipoDB).order_by(SancionTipoDB.codigo).all()
        items = []
        for t in tipos:
            items.append({
                'id': t.id,
                'codigo': t.codigo,
                'descripcion': t.descripcion,
                'usuario_creacion': t.usuario_creacion,
                'creado_en': t.creado_en.isoformat() + 'Z',
                'actualizado_en': t.actualizado_en.isoformat() + 'Z'
            })
        return jsonify(items)
    finally:
        db.close()


@app.get('/api/sancion-tipos/<tipo_id>')
def sancion_tipo_obtener(tipo_id: str):
    """Obtener un tipo de sanción por ID"""
    db = SessionLocal()
    try:
        tipo = db.get(SancionTipoDB, tipo_id)
        if not tipo:
            return jsonify({"error": "Tipo de sanción no encontrado"}), 404
        return jsonify({
            'id': tipo.id,
            'codigo': tipo.codigo,
            'descripcion': tipo.descripcion,
            'usuario_creacion': tipo.usuario_creacion,
            'creado_en': tipo.creado_en.isoformat() + 'Z',
            'actualizado_en': tipo.actualizado_en.isoformat() + 'Z'
        })
    finally:
        db.close()


@app.post('/api/sancion-tipos')
def sancion_tipo_crear():
    """Crear un nuevo tipo de sanción con validaciones RB1-RB4"""
    data = request.get_json(silent=True) or request.form.to_dict()
    
    codigo = data.get('codigo', '').strip() if data.get('codigo') else ''
    descripcion = data.get('descripcion', '').strip() if data.get('descripcion') else ''
    usuario_creacion = data.get('usuario_creacion')  # Opcional para auditoría
    
    db = SessionLocal()
    try:
        # Separar validaciones de persistencia (flujo éxito/error)
        errores, codigo_validado, descripcion_validada = validar_sancion_tipo(codigo, descripcion, db)
        if errores:
            # Mensajes de error claros y específicos por validación
            return jsonify({"ok": False, "error": errores[0]}), 400
        
        # Crear registro con auditoría usando valores validados
        now = datetime.utcnow()
        tipo = SancionTipoDB(
            id=str(uuid.uuid4()),
            codigo=codigo_validado,
            descripcion=descripcion_validada,
            usuario_creacion=usuario_creacion,
            creado_en=now,
            actualizado_en=now
        )
        
        db.add(tipo)
        db.commit()
        
        return jsonify({
            "ok": True,
            "id": tipo.id,
            "codigo": tipo.codigo,
            "descripcion": tipo.descripcion,
            "mensaje": "Registro exitoso"
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"Error al crear tipo de sanción: {str(e)}"}), 500
    finally:
        db.close()


@app.put('/api/sancion-tipos/<tipo_id>')
def sancion_tipo_actualizar(tipo_id: str):
    """Actualizar un tipo de sanción existente"""
    data = request.get_json(silent=True) or request.form.to_dict()
    
    codigo = data.get('codigo', '').strip() if data.get('codigo') else ''
    descripcion = data.get('descripcion', '').strip() if data.get('descripcion') else ''
    
    db = SessionLocal()
    try:
        tipo = db.get(SancionTipoDB, tipo_id)
        if not tipo:
            return jsonify({"ok": False, "error": "Tipo de sanción no encontrado"}), 404
        
        # Validar con exclusión del ID actual
        errores, codigo_validado, descripcion_validada = validar_sancion_tipo(codigo, descripcion, db, excluir_id=tipo_id)
        if errores:
            return jsonify({"ok": False, "error": errores[0]}), 400
        
        # Actualizar campos con valores validados
        tipo.codigo = codigo_validado
        tipo.descripcion = descripcion_validada
        tipo.actualizado_en = datetime.utcnow()
        
        db.commit()
        
        return jsonify({
            "ok": True,
            "id": tipo.id,
            "codigo": tipo.codigo,
            "descripcion": tipo.descripcion,
            "mensaje": "Tipo de sanción actualizado correctamente"
        })
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"Error al actualizar tipo de sanción: {str(e)}"}), 500
    finally:
        db.close()


@app.delete('/api/sancion-tipos/<tipo_id>')
def sancion_tipo_eliminar(tipo_id: str):
    """Eliminar un tipo de sanción"""
    db = SessionLocal()
    try:
        tipo = db.get(SancionTipoDB, tipo_id)
        if not tipo:
            return jsonify({"ok": False, "error": "Tipo de sanción no encontrado"}), 404
        
        db.delete(tipo)
        db.commit()
        
        return jsonify({"ok": True, "mensaje": "Tipo de sanción eliminado correctamente"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": f"Error al eliminar tipo de sanción: {str(e)}"}), 500
    finally:
        db.close()


def create_app():
    return app


def migrar_base_datos():
    """Agrega columnas faltantes y crea tablas nuevas si no existen"""
    db = SessionLocal()
    try:
        # Crear tabla mensajes si no existe
        try:
            db.execute(text("SELECT 1 FROM mensajes LIMIT 1"))
        except Exception:
            try:
                db.execute(text("""
                    CREATE TABLE mensajes (
                        id TEXT PRIMARY KEY,
                        id_remitente TEXT NOT NULL,
                        id_destinatario TEXT NOT NULL,
                        asunto TEXT,
                        contenido TEXT NOT NULL,
                        leido INTEGER NOT NULL DEFAULT 0,
                        relacionado_con TEXT,
                        tipo TEXT,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """))
                db.commit()
                print("✓ Tabla mensajes creada")
            except Exception as e:
                print(f"Error creando tabla mensajes: {e}")
        
        # Verificar y agregar codigo_inventario si no existe
        try:
            db.execute(text("SELECT codigo_inventario FROM libros LIMIT 1"))
        except Exception:
            print("Agregando columna codigo_inventario a la tabla libros...")
            db.execute(text("ALTER TABLE libros ADD COLUMN codigo_inventario VARCHAR(128)"))
            db.commit()
            print("✓ Columna codigo_inventario agregada correctamente")
        
        # Migrar columna autor para permitir NULL (SQLite no soporta ALTER COLUMN directamente)
        try:
            # Verificar si la columna autor tiene restricción NOT NULL
            result = db.execute(text("PRAGMA table_info(libros)"))
            columns = result.fetchall()
            autor_col = None
            for col in columns:
                if col[1] == 'autor':  # col[1] es el nombre de la columna
                    autor_col = col
                    break
            
            if autor_col and autor_col[3] == 1:  # col[3] es notnull (1 = NOT NULL, 0 = NULL permitido)
                print("Migrando columna autor para permitir NULL...")
                # SQLite no soporta cambiar NOT NULL directamente, necesitamos recrear la tabla
                db.execute(text("""
                    CREATE TABLE libros_new (
                        id VARCHAR(64) PRIMARY KEY,
                        titulo VARCHAR(255) NOT NULL,
                        autor VARCHAR(255),
                        isbn VARCHAR(64),
                        editorial VARCHAR(255),
                        anio_publicacion INTEGER,
                        categoria VARCHAR(128),
                        subcategoria VARCHAR(128),
                        descripcion TEXT,
                        estado_disponibilidad VARCHAR(64),
                        estado_elemento VARCHAR(64),
                        stock INTEGER DEFAULT 0,
                        cantidad_disponible INTEGER DEFAULT 0,
                        cantidad_prestado INTEGER DEFAULT 0,
                        imagen VARCHAR(512),
                        codigo_inventario VARCHAR(128),
                        creado_en DATETIME NOT NULL,
                        actualizado_en DATETIME NOT NULL
                    )
                """))
                
                # Copiar datos existentes
                db.execute(text("""
                    INSERT INTO libros_new 
                    SELECT id, titulo, autor, isbn, editorial, anio_publicacion, categoria, subcategoria,
                           descripcion, estado_disponibilidad, estado_elemento,
                           stock, cantidad_disponible, cantidad_prestado,
                           imagen, codigo_inventario, creado_en, actualizado_en
                    FROM libros
                """))
                
                # Crear índices si existen en la tabla original
                try:
                    db.execute(text("CREATE INDEX IF NOT EXISTS idx_libros_categoria ON libros_new(categoria)"))
                    db.execute(text("CREATE INDEX IF NOT EXISTS idx_libros_codigo_inv ON libros_new(codigo_inventario)"))
                except Exception:
                    pass
                
                # Eliminar tabla vieja y renombrar la nueva
                db.execute(text("DROP TABLE libros"))
                db.execute(text("ALTER TABLE libros_new RENAME TO libros"))
                db.commit()
                print("✓ Columna autor migrada correctamente (ahora permite NULL)")
            else:
                print("✓ Campo autor ya permite NULL (para equipos/PCs)")
        except Exception as e:
            print(f"⚠️  Error en migración de autor: {e}")
            print("   Continuando... (se usará valor por defecto para equipos)")
            db.rollback()
        
        # Verificar y agregar columnas al modelo UserDB si no existen
        try:
            db.execute(text("SELECT tipo_documento FROM usuarios LIMIT 1"))
        except Exception:
            print("Agregando columnas nuevas a la tabla usuarios...")
            try:
                db.execute(text("ALTER TABLE usuarios ADD COLUMN tipo_documento VARCHAR(10)"))
            except Exception:
                pass
            try:
                db.execute(text("ALTER TABLE usuarios ADD COLUMN numero_ficha VARCHAR(64)"))
            except Exception:
                pass
            try:
                db.execute(text("ALTER TABLE usuarios ADD COLUMN direccion VARCHAR(255)"))
            except Exception:
                pass
            try:
                db.execute(text("ALTER TABLE usuarios ADD COLUMN telefono VARCHAR(64)"))
            except Exception:
                pass
            try:
                db.execute(text("ALTER TABLE usuarios ADD COLUMN tipo_usuario VARCHAR(10)"))
            except Exception:
                pass
            db.commit()
            print("✓ Columnas de usuarios agregadas correctamente")
        
        # Crear tabla sancion_tipo si no existe
        try:
            db.execute(text("SELECT 1 FROM sancion_tipo LIMIT 1"))
        except Exception:
            try:
                db.execute(text("""
                    CREATE TABLE sancion_tipo (
                        id TEXT PRIMARY KEY,
                        codigo TEXT NOT NULL UNIQUE,
                        descripcion TEXT NOT NULL,
                        usuario_creacion TEXT,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """))
                db.commit()
                print("✓ Tabla sancion_tipo creada")
            except Exception as e:
                print(f"Error creando tabla sancion_tipo: {e}")
        
        # Crear tabla libro_historial si no existe
        try:
            db.execute(text("SELECT 1 FROM libro_historial LIMIT 1"))
        except Exception:
            try:
                db.execute(text("""
                    CREATE TABLE libro_historial (
                        id TEXT PRIMARY KEY,
                        id_libro_original TEXT NOT NULL,
                        titulo TEXT NOT NULL,
                        autor TEXT,
                        isbn TEXT,
                        codigo_inventario TEXT,
                        categoria TEXT,
                        motivo_eliminacion TEXT,
                        datos_completos TEXT,
                        usuario_eliminador TEXT,
                        fecha_eliminacion TEXT NOT NULL,
                        prestamos_relacionados INTEGER DEFAULT 0,
                        favoritos_relacionados INTEGER DEFAULT 0
                    )
                """))
                db.commit()
                print("✓ Tabla libro_historial creada")
            except Exception as e:
                print(f"Error creando tabla libro_historial: {e}")
    except Exception as e:
        print(f"Error en migración: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    # Configuración desde variables de entorno
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    
    Base.metadata.create_all(bind=engine)
    migrar_base_datos()  # Migrar base de datos existente
    
    # Obtener la IP local automáticamente
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        print("=" * 60)
        print("🚀 SERVIDOR INICIADO")
        print("=" * 60)
        print(f"📍 Acceso desde esta computadora:")
        print(f"   http://localhost:{port}")
        print(f"   http://127.0.0.1:{port}")
        print(f"\n📱 Acceso desde otros dispositivos (celular, tablet):")
        print(f"   http://{ip_local}:{port}")
        print(f"\n⚠️  IMPORTANTE: Asegúrate de que ambos dispositivos")
        print(f"   estén en la misma red WiFi")
        if debug:
            print(f"\n⚠️  MODO DEBUG ACTIVADO (solo para desarrollo)")
        print("=" * 60)
    except Exception:
        ip_local = "TU_IP_LOCAL"
        print(f"⚠️  Ejecutando en: http://{host}:{port}")
        print(f"📱 Para acceder desde tu celular, necesitas tu IP local")
        if debug:
            print(f"\n⚠️  MODO DEBUG ACTIVADO (solo para desarrollo)")
    
    app.run(host=host, port=port, debug=debug)



