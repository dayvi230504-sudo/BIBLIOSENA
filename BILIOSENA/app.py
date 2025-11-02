from __future__ import annotations
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import logging
from logging.handlers import RotatingFileHandler

# ===================================
# 🔧 CONFIGURACIÓN GENERAL
# ===================================

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Configuración de logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/bibliosena.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('BIBLIOSENA startup')

# Base de datos: PostgreSQL (Render) o SQLite (local)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///./bibliosena.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

db = SQLAlchemy(app)


# ===================================
# 🛡️ MIDDLEWARE DE AUTENTICACIÓN
# ===================================

def require_auth(f):
    """Decorador para requerir autenticación"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "Token de autenticación requerido"}), 401
        
        try:
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            # Verificación simple del token (en producción usar JWT real)
            if not token.startswith('admin-') and not token.startswith('user-'):
                return jsonify({"error": "Token inválido"}), 401
            
            usuario_id = int(token.split('-')[1]) if '-' in token else None
            request.current_user_id = usuario_id
            request.current_token = token
            
        except Exception as e:
            app.logger.error(f"Error en autenticación: {str(e)}")
            return jsonify({"error": "Token inválido"}), 401
        
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorador para requerir rol de administrador"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').split(' ')[1] if ' ' in request.headers.get('Authorization', '') else request.headers.get('Authorization', '')
        
        if not token or not token.startswith('admin-'):
            return jsonify({"error": "Acceso denegado. Se requiere rol de administrador"}), 403
        
        return f(*args, **kwargs)
    return decorated


# ===================================
# 🧱 MODELOS
# ===================================

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)  # Aumentado para hash
    rol = db.Column(db.String(50), default="lector")
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hashea la contraseña"""
        self.contraseña = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.contraseña, password)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "correo": self.correo,
            "rol": self.rol,
            "fecha_registro": self.fecha_registro.strftime("%Y-%m-%d %H:%M:%S"),
        }


class Libro(db.Model):
    __tablename__ = "libros"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    autor = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(100))
    descripcion = db.Column(db.Text)
    stock = db.Column(db.Integer, default=1)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "autor": self.autor,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
            "stock": self.stock,
            "fecha_creacion": self.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S"),
        }


class Prestamo(db.Model):
    __tablename__ = "prestamos"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    libro_id = db.Column(db.Integer, db.ForeignKey("libros.id"), nullable=False)
    fecha_prestamo = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_devolucion = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default="prestado")

    usuario = db.relationship("Usuario", backref="prestamos")
    libro = db.relationship("Libro", backref="prestamos")

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "libro_id": self.libro_id,
            "usuario": self.usuario.nombre if self.usuario else None,
            "libro": self.libro.titulo if self.libro else None,
            "fecha_prestamo": self.fecha_prestamo.strftime("%Y-%m-%d"),
            "fecha_devolucion": self.fecha_devolucion.strftime("%Y-%m-%d") if self.fecha_devolucion else None,
            "estado": self.estado,
        }


# ===================================
# 🌐 RUTAS DE USUARIOS
# ===================================

@app.route("/api/usuarios", methods=["GET"])
@require_auth
@require_admin
def listar_usuarios():
    """Listar todos los usuarios (solo admin)"""
    try:
        usuarios = Usuario.query.all()
        return jsonify([u.to_dict() for u in usuarios]), 200
    except Exception as e:
        app.logger.error(f"Error listando usuarios: {str(e)}")
        return jsonify({"error": "Error al listar usuarios"}), 500


@app.route("/api/usuarios", methods=["POST"])
def crear_usuario():
    """Crear nuevo usuario"""
    try:
        data = request.get_json()
        
        # Validación
        if not data or not data.get("correo") or not data.get("contraseña"):
            return jsonify({"error": "Datos incompletos. Se requiere correo y contraseña"}), 400
        
        if len(data.get("contraseña", "")) < 6:
            return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
        
        if Usuario.query.filter_by(correo=data["correo"]).first():
            return jsonify({"error": "El correo ya está registrado"}), 409

        nuevo = Usuario(
            nombre=data.get("nombre", "Usuario"),
            correo=data["correo"],
            rol=data.get("rol", "lector"),
        )
        nuevo.set_password(data["contraseña"])
        
        db.session.add(nuevo)
        db.session.commit()
        
        app.logger.info(f"Usuario creado: {nuevo.correo}")
        return jsonify({"mensaje": "Usuario creado correctamente", "usuario": nuevo.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creando usuario: {str(e)}")
        return jsonify({"error": "Error al crear usuario"}), 500


@app.route("/api/login", methods=["POST"])
def login():
    """Iniciar sesión y obtener token"""
    try:
        data = request.get_json()
        
        if not data or not data.get("correo") or not data.get("contraseña"):
            return jsonify({"error": "Correo y contraseña requeridos"}), 400
        
        usuario = Usuario.query.filter_by(correo=data.get("correo")).first()
        
        if not usuario or not usuario.check_password(data.get("contraseña")):
            app.logger.warning(f"Intento de login fallido: {data.get('correo')}")
            return jsonify({"error": "Credenciales inválidas"}), 401
        
        # Generar token simple (en producción usar JWT)
        token = f"{usuario.rol}-{usuario.id}"
        
        app.logger.info(f"Login exitoso: {usuario.correo} ({usuario.rol})")
        
        response = usuario.to_dict()
        response["token"] = token
        return jsonify(response), 200
    
    except Exception as e:
        app.logger.error(f"Error en login: {str(e)}")
        return jsonify({"error": "Error al iniciar sesión"}), 500


# ===================================
# 📚 RUTAS DE LIBROS
# ===================================

@app.route("/api/libros", methods=["GET"])
def listar_libros():
    """Listar todos los libros (público)"""
    try:
        libros = Libro.query.all()
        return jsonify([l.to_dict() for l in libros]), 200
    except Exception as e:
        app.logger.error(f"Error listando libros: {str(e)}")
        return jsonify({"error": "Error al listar libros"}), 500


@app.route("/api/libros", methods=["POST"])
@require_auth
@require_admin
def crear_libro():
    """Crear nuevo libro (solo admin)"""
    try:
        data = request.get_json()
        
        # Validación
        if not data or not data.get("titulo") or not data.get("autor"):
            return jsonify({"error": "Título y autor son requeridos"}), 400
        
        if data.get("stock", 0) < 0:
            return jsonify({"error": "El stock no puede ser negativo"}), 400
        
        nuevo = Libro(
            titulo=data.get("titulo"),
            autor=data.get("autor"),
            categoria=data.get("categoria"),
            descripcion=data.get("descripcion"),
            stock=data.get("stock", 1),
        )
        
        db.session.add(nuevo)
        db.session.commit()
        
        app.logger.info(f"Libro creado: {nuevo.titulo}")
        return jsonify({"mensaje": "Libro agregado correctamente", "libro": nuevo.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creando libro: {str(e)}")
        return jsonify({"error": "Error al crear libro"}), 500


@app.route("/api/libros/<int:id>", methods=["GET"])
def obtener_libro(id):
    """Obtener un libro por ID"""
    try:
        libro = Libro.query.get(id)
        if not libro:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify(libro.to_dict()), 200
    except Exception as e:
        app.logger.error(f"Error obteniendo libro: {str(e)}")
        return jsonify({"error": "Error al obtener libro"}), 500


@app.route("/api/libros/<int:id>", methods=["PUT"])
@require_auth
@require_admin
def editar_libro(id):
    """Editar un libro (solo admin)"""
    try:
        libro = Libro.query.get(id)
        if not libro:
            return jsonify({"error": "Libro no encontrado"}), 404

        data = request.get_json()
        
        # Validación
        if data.get("stock") is not None and data.get("stock") < 0:
            return jsonify({"error": "El stock no puede ser negativo"}), 400
        
        libro.titulo = data.get("titulo", libro.titulo)
        libro.autor = data.get("autor", libro.autor)
        libro.categoria = data.get("categoria", libro.categoria)
        libro.descripcion = data.get("descripcion", libro.descripcion)
        
        if "stock" in data:
            libro.stock = data.get("stock")
        
        db.session.commit()
        
        app.logger.info(f"Libro actualizado: {libro.titulo}")
        return jsonify({"mensaje": "Libro actualizado correctamente", "libro": libro.to_dict()}), 200
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error actualizando libro: {str(e)}")
        return jsonify({"error": "Error al actualizar libro"}), 500


@app.route("/api/libros/<int:id>", methods=["DELETE"])
@require_auth
@require_admin
def eliminar_libro(id):
    """Eliminar un libro (solo admin)"""
    try:
        libro = Libro.query.get(id)
        if not libro:
            return jsonify({"error": "Libro no encontrado"}), 404
        
        titulo = libro.titulo
        db.session.delete(libro)
        db.session.commit()
        
        app.logger.info(f"Libro eliminado: {titulo}")
        return jsonify({"mensaje": "Libro eliminado correctamente"}), 200
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error eliminando libro: {str(e)}")
        return jsonify({"error": "Error al eliminar libro"}), 500


# ===================================
# 📖 RUTAS DE PRÉSTAMOS
# ===================================

@app.route("/api/prestamos", methods=["GET"])
@require_auth
def listar_prestamos():
    """Listar préstamos (usuarios ven solo los suyos, admin ve todos)"""
    try:
        token = request.headers.get('Authorization', '').split(' ')[1] if ' ' in request.headers.get('Authorization', '') else request.headers.get('Authorization', '')
        
        if token and token.startswith('admin-'):
            # Admin ve todos
            prestamos = Prestamo.query.all()
        else:
            # Usuario ve solo los suyos
            usuario_id = int(token.split('-')[1]) if '-' in token else None
            prestamos = Prestamo.query.filter_by(usuario_id=usuario_id).all()
        
        return jsonify([p.to_dict() for p in prestamos]), 200
    except Exception as e:
        app.logger.error(f"Error listando préstamos: {str(e)}")
        return jsonify({"error": "Error al listar préstamos"}), 500


@app.route("/api/prestamos", methods=["POST"])
@require_auth
def crear_prestamo():
    """Crear nuevo préstamo"""
    try:
        data = request.get_json()
        usuario_id = data.get("usuario_id")
        libro_id = data.get("libro_id")
        
        # Validación
        if not usuario_id or not libro_id:
            return jsonify({"error": "usuario_id y libro_id son requeridos"}), 400
        
        # Verificar que el usuario existe
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Verificar que el libro existe
        libro = Libro.query.get(libro_id)
        if not libro:
            return jsonify({"error": "Libro no encontrado"}), 404
        
        if libro.stock <= 0:
            return jsonify({"error": "Libro no disponible"}), 400
        
        # Verificar que el usuario no tiene préstamos pendientes del mismo libro
        prestamo_pendiente = Prestamo.query.filter_by(
            usuario_id=usuario_id,
            libro_id=libro_id,
            estado="prestado"
        ).first()
        
        if prestamo_pendiente:
            return jsonify({"error": "Ya tienes un préstamo pendiente de este libro"}), 400

        prestamo = Prestamo(usuario_id=usuario_id, libro_id=libro_id)
        libro.stock -= 1
        
        db.session.add(prestamo)
        db.session.commit()
        
        app.logger.info(f"Préstamo creado: usuario {usuario_id}, libro {libro_id}")
        return jsonify({"mensaje": "Préstamo registrado", "prestamo": prestamo.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creando préstamo: {str(e)}")
        return jsonify({"error": "Error al crear préstamo"}), 500


@app.route("/api/prestamos/<int:id>/devolver", methods=["PUT"])
@require_auth
@require_admin
def devolver_libro(id):
    """Devolver un libro (solo admin)"""
    try:
        prestamo = Prestamo.query.get(id)
        if not prestamo:
            return jsonify({"error": "Préstamo no encontrado"}), 404
        
        if prestamo.estado == "devuelto":
            return jsonify({"error": "Este préstamo ya fue devuelto"}), 400

        prestamo.estado = "devuelto"
        prestamo.fecha_devolucion = datetime.utcnow()
        prestamo.libro.stock += 1
        
        db.session.commit()
        
        app.logger.info(f"Préstamo devuelto: {id}")
        return jsonify({"mensaje": "Libro devuelto correctamente", "prestamo": prestamo.to_dict()}), 200
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error devolviendo libro: {str(e)}")
        return jsonify({"error": "Error al devolver libro"}), 500


# ===================================
# 🧰 RUTAS ESTÁTICAS
# ===================================

@app.route("/")
def index():
    """Página de inicio - Login"""
    return render_template("login.html")


@app.route("/principal")
def principal_page():
    """Página principal (dashboard)"""
    return render_template("principal.html")


@app.route("/login")
def login_page():
    """Página de login"""
    return render_template("login.html")


@app.route("/registro")
def registro_page():
    """Página de registro"""
    return render_template("registro.html")


@app.route("/libros")
def libros_page():
    """Página de libros"""
    return render_template("libros.html")


@app.route("/equipos")
def equipos_page():
    """Página de equipos"""
    return render_template("equipos.html")


@app.route("/prestamo")
def prestamo_page():
    """Página de préstamos"""
    return render_template("prestamo.html")


@app.route("/recuperar")
def recuperar_page():
    """Página de recuperar contraseña"""
    return render_template("recuperar.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    """Servir archivos estáticos"""
    return send_from_directory(app.static_folder, filename)


# ===================================
# 🚀 INICIALIZACIÓN
# ===================================

def create_tables():
    """Crear tablas y usuario admin por defecto"""
    db.create_all()
    
    # Crear usuario admin por defecto si no existe
    try:
        admin = Usuario.query.filter_by(correo="admin@bibliosena.com").first()
        if not admin:
            admin = Usuario(
                nombre="Administrador",
                correo="admin@bibliosena.com",
                rol="admin"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Usuario admin creado por defecto: admin@bibliosena.com / admin123")
    except Exception as e:
        app.logger.error(f"Error al crear admin: {str(e)}")


# Inicializar base de datos al importar el módulo (importante para Gunicorn)
with app.app_context():
    create_tables()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
