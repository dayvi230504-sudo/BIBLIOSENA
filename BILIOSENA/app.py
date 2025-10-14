from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any

from flask import Flask, jsonify, request, send_from_directory, render_template
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from flask_cors import CORS
import os
import uuid


app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/static',
    template_folder='templates',
)
CORS(app)


# -------------------------------
# Dominio y almacenamiento en memoria
# -------------------------------

Base = declarative_base()


class LibroDB(Base):
    __tablename__ = "libros"
    id = Column(String(64), primary_key=True)
    titulo = Column(String(255), nullable=False)
    autor = Column(String(255), nullable=False)
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
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)


engine = create_engine("sqlite:///bibliosena.db", echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


def now_iso() -> str:
    return datetime.utcnow().isoformat() + 'Z'


def libro_from_request_db(data: Dict[str, Any]) -> LibroDB:
    now = datetime.utcnow()
    return LibroDB(
        id=str(uuid.uuid4()),
        titulo=data.get('titulo', ''),
        autor=data.get('autor', ''),
        isbn=data.get('isbn', ''),
        editorial=data.get('editorial', ''),
        anio_publicacion=int(data.get('anio_publicacion', 0) or 0),
        categoria=data.get('categoria', ''),
        subcategoria=data.get('subcategoria', ''),
        descripcion=data.get('descripcion', ''),
        estado_disponibilidad=data.get('estado_disponibilidad', 'Disponible'),
        estado_elemento=data.get('estado_elemento', 'Buen estado'),
        stock=int(data.get('stock', 0) or 0),
        cantidad_disponible=int(data.get('cantidad_disponible', 0) or 0),
        cantidad_prestado=int(data.get('cantidad_prestado', 0) or 0),
        imagen=None,
        creado_en=now,
        actualizado_en=now,
    )


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
# API mock: autenticación muy básica
# -------------------------------

@app.post('/api/login')
def api_login():
    payload = request.get_json(silent=True) or request.form
    user = (payload or {}).get('user') or (payload or {}).get('username')
    pwd = (payload or {}).get('password')
    if user == 'admin' and pwd == 'admin':
        return jsonify({"ok": True, "token": "fake-token", "user": {"name": "Administrador"}})
    return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401


# -------------------------------
# API CRUD de libros (en memoria)
# -------------------------------

@app.get('/api/libros')
def libros_listar():
    db = SessionLocal()
    try:
        rows = db.query(LibroDB).all()
        items = [
            {
                **{k: getattr(r, k) for k in ['id','titulo','autor','isbn','editorial','anio_publicacion','categoria','subcategoria','descripcion','estado_disponibilidad','estado_elemento','stock','cantidad_disponible','cantidad_prestado','imagen']},
                'creado_en': r.creado_en.isoformat() + 'Z',
                'actualizado_en': r.actualizado_en.isoformat() + 'Z',
            }
            for r in rows
        ]
        return jsonify(items)
    finally:
        db.close()


@app.post('/api/libros')
def libros_crear():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    db = SessionLocal()
    try:
        libro = libro_from_request_db(data)
        file = request.files.get('imagen') if 'imagen' in request.files else None
        if file and file.filename:
            uploads_dir = os.path.join('uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            save_path = os.path.join(uploads_dir, f"{libro.id}_{file.filename}")
            file.save(save_path)
            libro.imagen = save_path
        db.add(libro)
        db.commit()
        return jsonify({'id': libro.id}), 201
    finally:
        db.close()


@app.get('/api/libros/<libro_id>')
def libros_obtener(libro_id: str):
    db = SessionLocal()
    try:
        r = db.get(LibroDB, libro_id)
        if not r:
            return ("No encontrado", 404)
        item = {**{k: getattr(r, k) for k in ['id','titulo','autor','isbn','editorial','anio_publicacion','categoria','subcategoria','descripcion','estado_disponibilidad','estado_elemento','stock','cantidad_disponible','cantidad_prestado','imagen']}, 'creado_en': r.creado_en.isoformat()+'Z', 'actualizado_en': r.actualizado_en.isoformat()+'Z'}
        return jsonify(item)
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
    db = SessionLocal()
    try:
        r = db.get(LibroDB, libro_id)
        if not r:
            return ("No encontrado", 404)
        db.delete(r)
        db.commit()
        return ("", 204)
    finally:
        db.close()


def create_app():
    return app


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    Base.metadata.create_all(bind=engine)
    app.run(host='127.0.0.1', port=port, debug=True)


