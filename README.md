# 📚 BIBLIOSENA - Sistema de Gestión de Biblioteca

Sistema web moderno para la gestión de préstamos y sanciones de la biblioteca del SENA, desarrollado con Flask y diseño inspirado en Digitalia Publishing.

## ✨ Características

- 🎨 **Diseño Moderno**: Interfaz inspirada en Digitalia Publishing con efectos glassmorphism
- 📖 **Gestión de Libros**: Registro, consulta y administración de elementos bibliográficos
- 👥 **Gestión de Usuarios**: Sistema de registro y autenticación
- 🔄 **Préstamos**: Solicitud y seguimiento de préstamos de libros
- 🎯 **Carrusel Interactivo**: Navegación visual de nuevos títulos
- 📱 **Responsive**: Adaptable a diferentes dispositivos

## 🚀 Tecnologías

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **Base de Datos**: SQLite
- **Diseño**: CSS moderno con gradientes y animaciones

## 📁 Estructura del Proyecto

```
BIBLIOSENA/
├── BILIOSENA/
│   ├── static/
│   │   ├── css/           # Estilos CSS
│   │   ├── js/            # JavaScript
│   │   └── uploads/       # Imágenes de libros
│   ├── templates/         # Plantillas HTML
│   ├── app.py            # Aplicación principal Flask
│   └── bibliosena.db     # Base de datos SQLite
├── .gitignore
└── README.md
```

## 🛠️ Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/TU_USUARIO/bibliosena.git
cd bibliosena
```

2. **Crear entorno virtual**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Instalar dependencias**
```bash
pip install flask
```

4. **Ejecutar la aplicación**
```bash
cd BILIOSENA
python app.py
```

5. **Abrir en el navegador**
```
http://localhost:5000
```

## 🎯 Funcionalidades

### 📚 Gestión de Libros
- Registro de nuevos elementos bibliográficos
- Consulta de disponibilidad
- Detalles completos de cada libro
- Categorización por temas

### 👤 Gestión de Usuarios
- Registro de nuevos usuarios
- Autenticación segura
- Perfiles de aprendices e instructores

### 🔄 Sistema de Préstamos
- Solicitud de préstamos
- Seguimiento de fechas de devolución
- Control de disponibilidad

### 🎨 Interfaz Moderna
- Diseño glassmorphism
- Gradientes modernos
- Animaciones suaves
- Carrusel interactivo

## 🤝 Colaboración

### Para colaborar en el proyecto:

1. **Fork del repositorio**
2. **Crear una rama para tu feature**
```bash
git checkout -b feature/nueva-funcionalidad
```

3. **Hacer commits descriptivos**
```bash
git commit -m "Agregar funcionalidad de búsqueda avanzada"
```

4. **Push a tu rama**
```bash
git push origin feature/nueva-funcionalidad
```

5. **Crear Pull Request**

## 📝 Convenciones de Código

- **CSS**: Usar nomenclatura BEM
- **JavaScript**: Usar camelCase
- **Python**: Seguir PEP 8
- **Commits**: Usar mensajes descriptivos en español

## 🎨 Paleta de Colores

- **Gradiente Principal**: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- **Texto Principal**: `#2c3e50`
- **Texto Secundario**: `#555`
- **Bordes**: `#e1e8ed`

## 📱 Páginas Disponibles

- `/` - Página de inicio/login
- `/principal` - Dashboard principal
- `/registro` - Registro de usuarios
- `/libro` - Registro de libros
- `/prestamo` - Solicitud de préstamos
- `/detalle_libro` - Detalles del libro

## 🐛 Reportar Issues

Si encuentras algún problema:
1. Verifica que no exista un issue similar
2. Crea un nuevo issue con descripción detallada
3. Incluye pasos para reproducir el error

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 👥 Contribuidores

- **Santo** - Desarrollador Principal

---

⭐ **¡Dale una estrella al proyecto si te gusta!** ⭐