# 🚀 Guía de Despliegue - BIBLIOSENA en Render

Esta guía te ayudará a desplegar tu aplicación BIBLIOSENA en Render para que pueda ser accesible desde internet.

## 📋 Requisitos Previos

1. ✅ Tu código en GitHub (ya lo tienes)
2. ✅ Una cuenta en [Render.com](https://render.com) (gratis)
3. ✅ Tu amigo como colaborador en GitHub (ya lo tienes)

---

## 🎯 Paso 1: Crear cuenta en Render

1. Ve a [https://render.com](https://render.com)
2. Haz clic en **"Get Started for Free"** o **"Sign Up"**
3. Conecta tu cuenta de **GitHub**
4. Autoriza a Render para acceder a tus repositorios

---

## 🎯 Paso 2: Crear nuevo Web Service

1. En el dashboard de Render, haz clic en **"New +"** → **"Web Service"**
2. Selecciona tu repositorio: **dayvi230504-sudo/BIBLIOSENA**
3. Configura el servicio:
   - **Name**: `bibliosena` (o el nombre que prefieras)
   - **Region**: Elige la más cercana (ej: `Oregon` para USA, `Frankfurt` para Europa)
   - **Branch**: `main`
   - **Root Directory**: (dejar vacío)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd BILIOSENA && gunicorn app:app --bind 0.0.0.0:$PORT`

---

## 🎯 Paso 3: Variables de Entorno

En la sección **"Environment Variables"**, agrega:

1. **SECRET_KEY**: 
   - Genera una clave secreta (puedes usar: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - O Render puede generarla automáticamente

2. **FLASK_DEBUG**: 
   - Valor: `0` (para producción)

3. **PORT**: 
   - Render lo asigna automáticamente, no necesitas agregarlo

**Opcional:**
- Si quieres usar PostgreSQL en lugar de SQLite:
  - Render puede crear una base de datos PostgreSQL automáticamente
  - Ve a "New +" → "PostgreSQL"
  - Luego agrega la variable `DATABASE_URL` con la URL que Render te da

---

## 🎯 Paso 4: Desplegar

1. Haz clic en **"Create Web Service"**
2. Render comenzará a construir y desplegar tu aplicación
3. Espera 5-10 minutos (primera vez puede tardar más)
4. Verás el progreso en tiempo real

---

## 🎯 Paso 5: Configurar Base de Datos

### Opción A: Usar SQLite (más simple, pero limitado)
- La base de datos SQLite se creará automáticamente
- ⚠️ Nota: SQLite puede tener problemas con múltiples usuarios simultáneos
- ⚠️ Los datos se pierden si el servicio se reinicia (en el plan gratuito)

### Opción B: Usar PostgreSQL (recomendado para producción)
1. En Render, ve a **"New +" → "PostgreSQL"**
2. Configura:
   - **Name**: `bibliosena-db`
   - **Database**: `bibliosena`
   - **User**: (se genera automáticamente)
   - **Region**: La misma que tu web service
3. Copia la **Internal Database URL**
4. Ve a tu Web Service → **Environment** → Agrega:
   - **Key**: `DATABASE_URL`
   - **Value**: La URL que copiaste
5. Reinicia el servicio

---

## 🎯 Paso 6: Acceder a tu aplicación

Una vez desplegado, Render te dará una URL como:
```
https://bibliosena.onrender.com
```

✅ **¡Ya puedes compartir esta URL con tu amigo!**

---

## 🔐 Configurar Usuario Admin

1. Visita tu aplicación desplegada
2. Ve a `/login.html`
3. Inicia sesión con:
   - Usuario: `admin`
   - Contraseña: `admin`
4. ⚠️ **IMPORTANTE**: Cambia la contraseña del admin inmediatamente después del primer acceso

---

## 👥 Compartir con tu Amigo

### Opción 1: Solo acceso a la aplicación
- Comparte la URL de Render
- Tu amigo puede usar la aplicación normalmente

### Opción 2: Dar acceso de colaborador en Render
1. En tu Web Service en Render
2. Ve a **"Settings" → "Collaborators"**
3. Haz clic en **"Add Collaborator"**
4. Ingresa el email de GitHub de tu amigo
5. Tu amigo recibirá una invitación

---

## 📝 Notas Importantes

### Plan Gratuito de Render:
- ✅ Gratis para siempre
- ⚠️ El servicio se "duerme" después de 15 minutos de inactividad
- ⚠️ La primera petición después de dormir puede tardar 30-60 segundos
- ⚠️ 512 MB de RAM (suficiente para esta app)
- ⚠️ SQLite puede resetearse en reinicios (usa PostgreSQL para datos persistentes)

### Mejores Prácticas:
1. **Cambiar contraseñas por defecto** inmediatamente
2. **Usar PostgreSQL** para producción (no SQLite)
3. **Hacer backups** periódicos de la base de datos
4. **Monitorear logs** en Render dashboard

---

## 🐛 Solución de Problemas

### Error: "Module not found"
- Verifica que `requirements.txt` tenga todas las dependencias
- Revisa los logs en Render

### Error: "Database locked"
- Cambia a PostgreSQL en lugar de SQLite

### Error: "Application failed to respond"
- Verifica que el `Start Command` sea correcto
- Revisa los logs de build

### La aplicación tarda mucho en cargar
- Es normal en el plan gratuito (se "duerme" después de inactividad)
- Considera usar un servicio como [UptimeRobot](https://uptimerobot.com) para mantenerla activa

---

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en Render Dashboard
2. Verifica que todos los archivos estén en GitHub
3. Asegúrate de que las variables de entorno estén configuradas

¡Éxito con tu despliegue! 🚀

