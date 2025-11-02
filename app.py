from __future__ import annotations
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# ===================================
# 🔧 CONFIGURACIÓN GENERAL
# ===================================

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Base de datos: PostgreSQL (Render) o SQLite (local)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///bibliosena.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ===================================
# 🧱 MODELOS
# ===================================

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contraseña = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(50), default="lector")
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

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
def listar_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([u.to_dict() for u in usuarios])


@app.route("/api/usuarios", methods=["POST"])
def crear_usuario():
    data = request.get_json()
    if not data.get("correo") or not data.get("contraseña"):
        return jsonify({"error": "Datos incompletos"}), 400
    if Usuario.query.filter_by(correo=data["correo"]).first():
        return jsonify({"error": "El correo ya está registrado"}), 409

    nuevo = Usuario(
        nombre=data.get("nombre"),
        correo=data["correo"],
        contraseña=data["contraseña"],
        rol=data.get("rol", "lector"),
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"mensaje": "Usuario creado correctamente"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(correo=data.get("correo")).first()
    if not usuario or usuario.contraseña != data.get("contraseña"):
        return jsonify({"error": "Credenciales inválidas"}), 401
    return jsonify(usuario.to_dict())


# ===================================
# 📚 RUTAS DE LIBROS
# ===================================

@app.route("/api/libros", methods=["GET"])
def listar_libros():
    libros = Libro.query.all()
    return jsonify([l.to_dict() for l in libros])


@app.route("/api/libros", methods=["POST"])
def crear_libro():
    data = request.get_json()
    nuevo = Libro(
        titulo=data.get("titulo"),
        autor=data.get("autor"),
        categoria=data.get("categoria"),
        descripcion=data.get("descripcion"),
        stock=data.get("stock", 1),
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"mensaje": "Libro agregado correctamente"}), 201


@app.route("/api/libros/<int:id>", methods=["PUT"])
def editar_libro(id):
    libro = Libro.query.get(id)
    if not libro:
        return jsonify({"error": "Libro no encontrado"}), 404

    data = request.get_json()
    libro.titulo = data.get("titulo", libro.titulo)
    libro.autor = data.get("autor", libro.autor)
    libro.categoria = data.get("categoria", libro.categoria)
    libro.descripcion = data.get("descripcion", libro.descripcion)
    libro.stock = data.get("stock", libro.stock)
    db.session.commit()
    return jsonify({"mensaje": "Libro actualizado correctamente"}), 200


@app.route("/api/libros/<int:id>", methods=["DELETE"])
def eliminar_libro(id):
    libro = Libro.query.get(id)
    if not libro:
        return jsonify({"error": "Libro no encontrado"}), 404
    db.session.delete(libro)
    db.session.commit()
    return jsonify({"mensaje": "Libro eliminado"}), 200


# ===================================
# 📖 RUTAS DE PRÉSTAMOS
# ===================================

@app.route("/api/prestamos", methods=["GET"])
def listar_prestamos():
    prestamos = Prestamo.query.all()
    return jsonify([p.to_dict() for p in prestamos])


@app.route("/api/prestamos", methods=["POST"])
def crear_prestamo():
    data = request.get_json()
    usuario_id = data.get("usuario_id")
    libro_id = data.get("libro_id")

    libro = Libro.query.get(libro_id)
    if not libro or libro.stock <= 0:
        return jsonify({"error": "Libro no disponible"}), 400

    prestamo = Prestamo(usuario_id=usuario_id, libro_id=libro_id)
    libro.stock -= 1
    db.session.add(prestamo)
    db.session.commit()
    return jsonify({"mensaje": "Préstamo registrado"}), 201


@app.route("/api/prestamos/<int:id>/devolver", methods=["PUT"])
def devolver_libro(id):
    prestamo = Prestamo.query.get(id)
    if not prestamo:
        return jsonify({"error": "Préstamo no encontrado"}), 404

    prestamo.estado = "devuelto"
    prestamo.fecha_devolucion = datetime.utcnow()
    prestamo.libro.stock += 1
    db.session.commit()
    return jsonify({"mensaje": "Libro devuelto correctamente"}), 200


# ===================================
# 🧰 RUTAS ESTÁTICAS
# ===================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


# ===================================
# 🚀 INICIALIZACIÓN
# ===================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crear tablas si no existen
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
