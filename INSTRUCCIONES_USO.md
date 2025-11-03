# 📋 Instrucciones de Uso - BIBLIOSENA

## 🚀 Iniciar la Aplicación

### Opción 1: Modo Desarrollo
```bash
cd BIBLIOSENA/BILIOSENA
python app.py
```

### Opción 2: Usando Gunicorn (Producción)
```bash
cd BIBLIOSENA
gunicorn BILIOSENA.app:app --bind 0.0.0.0:5000
```

## 🔐 Acceso Inicial

Al iniciar por primera vez, el sistema crea automáticamente un usuario administrador:

**Credenciales de Admin:**
- **Correo**: `admin@bibliosena.com`
- **Contraseña**: `admin123`

⚠️ **IMPORTANTE**: Cambia estas credenciales inmediatamente después del primer acceso en producción.

## 📍 Rutas de la Aplicación

- `/` - Página de login (inicio)
- `/login` - Página de login (alternativa)
- `/registro` - Registrar nuevo usuario
- `/principal` - Dashboard principal (requiere login)
- `/libros` - Catálogo de libros
- `/equipos` - Equipos disponibles
- `/prestamo` - Solicitar préstamo

## 📚 API Endpoints

### Usuarios
- `POST /api/login` - Iniciar sesión
- `POST /api/usuarios` - Crear usuario
- `GET /api/usuarios` - Listar usuarios (solo admin)

### Libros
- `GET /api/libros` - Listar todos los libros
- `GET /api/libros/<id>` - Obtener un libro
- `POST /api/libros` - Crear libro (admin)
- `PUT /api/libros/<id>` - Editar libro (admin)
- `DELETE /api/libros/<id>` - Eliminar libro (admin)

### Préstamos
- `GET /api/prestamos` - Listar préstamos
- `POST /api/prestamos` - Crear préstamo
- `PUT /api/prestamos/<id>/devolver` - Devolver libro (admin)

## 🔑 Autenticación

Todas las rutas de la API (excepto GET libros y login) requieren autenticación.

**Cómo autenticarse:**
1. Realizar POST a `/api/login` con correo y contraseña
2. El servidor responde con un `token`
3. Enviar el token en el header `Authorization`:
   ```
   Authorization: Bearer admin-1
   ```

## 📝 Crear Usuarios

Para crear un nuevo usuario:

**Endpoint:** `POST /api/usuarios`

**Body:**
```json
{
  "nombre": "Juan Pérez",
  "correo": "juan@example.com",
  "contraseña": "password123",
  "rol": "lector"
}
```

**Roles disponibles:**
- `lector` - Usuario normal
- `instructor` - Instructor
- `admin` - Administrador

## 📖 Crear Libros

Para crear un libro (solo admin):

**Endpoint:** `POST /api/libros`

**Headers:**
```
Authorization: Bearer admin-1
```

**Body:**
```json
{
  "titulo": "Don Quijote de la Mancha",
  "autor": "Miguel de Cervantes",
  "categoria": "Literatura",
  "descripcion": "Novela clásica española",
  "stock": 5
}
```

## 🔄 Manejo de Préstamos

### Crear Préstamo
**Endpoint:** `POST /api/prestamos`

**Headers:**
```
Authorization: Bearer lector-2
```

**Body:**
```json
{
  "usuario_id": 2,
  "libro_id": 1
}
```

### Devolver Libro
**Endpoint:** `PUT /api/prestamos/<id>/devolver`

**Headers:**
```
Authorization: Bearer admin-1
```

## 🐛 Solución de Problemas

### Base de datos no se crea
- Elimina `instance/bibliosena.db` si existe
- Reinicia la aplicación
- Verifica los logs en `logs/bibliosena.log`

### No puedo hacer login
- Verifica que el usuario existe
- Asegúrate de usar el correo completo
- Revisa la consola del navegador para errores

### Errores de permisos
- Solo admin puede crear/editar/eliminar libros
- Solo admin puede devolver préstamos
- Usuarios solo ven sus propios préstamos

### La aplicación no responde
- Verifica que el puerto 5000 no esté en uso
- Revisa los logs para errores
- Asegúrate de que todas las dependencias estén instaladas

## 📦 Dependencias Requeridas

Instalar todas las dependencias:
```bash
pip install -r requirements.txt
```

**Dependencias principales:**
- Flask 2.3.3
- Flask-SQLAlchemy 3.1.1
- Flask-CORS 6.0.1
- Werkzeug 2.3.7 (para hashing de contraseñas)
- gunicorn 21.2.0 (producción)

## 🔒 Seguridad

- ✅ Contraseñas hasheadas con werkzeug
- ✅ Autenticación basada en tokens
- ✅ Control de acceso por roles
- ✅ Validación de inputs
- ⚠️ **Todavía no implementado**: JWT, CSRF protection, rate limiting

## 📊 Base de Datos

**Desarrollo:** SQLite (archivo local)
**Producción:** PostgreSQL (Render)

**Modelos:**
- `Usuario` - Usuarios del sistema
- `Libro` - Libros y elementos bibliográficos
- `Prestamo` - Registro de préstamos

## 📞 Soporte

Si tienes problemas:
1. Revisa `logs/bibliosena.log`
2. Verifica la consola del navegador
3. Asegúrate de que la base de datos esté creada
4. Comprueba que todas las rutas estén correctamente configuradas

---

**Versión:** 2.0.0  
**Última actualización:** Noviembre 2024

