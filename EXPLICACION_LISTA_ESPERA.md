# 📋 ¿Para qué sirve la Lista de Espera?

## 🎯 Propósito

La **Lista de Espera** es un sistema automático que se activa cuando un usuario solicita un préstamo de un elemento (libro o equipo) que **no está disponible** en ese momento.

## 📖 Cómo Funciona

### 1. **Cuando un Usuario Solicita un Préstamo:**
   - El sistema verifica si hay unidades disponibles del elemento solicitado
   - Si hay disponibilidad → Se crea el préstamo en estado "pendiente"
   - Si NO hay disponibilidad → El usuario es **automáticamente agregado a la Lista de Espera**

### 2. **Cuando un Elemento se Devuelve:**
   - Cuando alguien devuelve un préstamo, el sistema revisa la lista de espera
   - Si hay personas esperando ese elemento, se les notifica (el admin puede ver quién está esperando)
   - El admin puede aprobar el préstamo a la primera persona en la lista

### 3. **Ventajas:**
   - ✅ Los usuarios no pierden su lugar en la cola
   - ✅ El admin sabe quién quiere el elemento cuando vuelve a estar disponible
   - ✅ Sistema justo: primero en solicitar, primero en recibir

## 🔍 Ejemplo Práctico

**Escenario:**
- Juan solicita el "Portátil A1" pero no hay disponibles
- María solicita el "Portátil A1" después de Juan
- El admin devuelve un "Portátil A1"

**Resultado:**
- Juan aparece primero en la lista de espera (lo solicitó primero)
- El admin puede aprobar el préstamo a Juan
- María sigue en la lista esperando el siguiente disponible

## 📊 Dónde Ver la Lista de Espera

- **Admin:** Panel de Administración → Sección "⏳ Lista de Espera"
- Se muestran: ID del elemento, contacto del usuario, fecha de solicitud, estado

## 🔔 Notificaciones

Cuando un elemento vuelve a estar disponible y hay personas en lista de espera, el admin recibe una notificación para poder gestionar los préstamos pendientes.



