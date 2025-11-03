# 📖 Cómo Borrar y Editar Libros

## 🗑️ BORRAR TODOS LOS LIBROS (Para importar CSV nuevo)

### Método 1: Desde el Panel de Admin (Más Fácil)

1. Inicia sesión como admin (`admin` / `admin`)
2. Ve a: `http://localhost:5000/admin.html`
3. Haz clic en "📚 Inventario" para expandir
4. Haz clic en el botón **"🗑️ Borrar Todos los Libros"**
5. Confirma escribiendo: `ELIMINAR TODO`
6. ¡Listo! Todos los libros están borrados

### Método 2: Página de Limpieza

1. Ve directamente a: `http://localhost:5000/limpiar_datos.html`
2. Verás un botón grande rojo: **"🗑️ BORRAR TODOS LOS LIBROS"**
3. Haz clic y confirma escribiendo: `ELIMINAR TODO`
4. Espera a que termine el proceso

### Método 3: Desde la Consola del Navegador

1. Abre la consola (F12)
2. Pega este código:

```javascript
fetch('/api/libros')
  .then(r => r.json())
  .then(async libros => {
    if (!confirm(`¿Eliminar ${libros.length} libros?`)) return;
    let eliminados = 0;
    for (const libro of libros) {
      await fetch(`/api/libros/${libro.id}`, { method: 'DELETE' });
      eliminados++;
      console.log(`Eliminados: ${eliminados}/${libros.length}`);
    }
    alert(`✓ ${eliminados} libros eliminados`);
  });
```

---

## ✏️ EDITAR LIBROS

### Desde la Página de Limpiar Datos

1. Ve a: `http://localhost:5000/limpiar_datos.html`
2. Haz clic en **"Editar Libro"**
3. Ingresa el **ID del libro** que quieres editar
   - Puedes obtener el ID desde la página principal haciendo clic en un libro (aparece en la URL)
4. Haz clic en **"Cargar Libro"**
5. Modifica los campos que necesites
6. Haz clic en **"Guardar Cambios"**

### Desde el Panel de Admin

1. En la sección "📚 Inventario"
2. Haz clic en **"Ver"** del libro que quieres editar
3. Esto te llevará a la página de detalles
4. (Puedes agregar un botón de edición allí si quieres)

---

## 📝 OBTENER EL ID DE UN LIBRO

**Método más fácil:**
1. Ve a la página principal (`principal.html`)
2. Haz clic en cualquier libro del carrusel
3. En la URL verás: `detalle_libro.html?id=ABC123-DEF456-GHI789`
4. El ID es: `ABC123-DEF456-GHI789` (copia esa parte)

---

## ⚠️ IMPORTANTE

- **Borrar libros NO borra préstamos ni sanciones**
- Si quieres limpiar todo, necesitarías borrar también préstamos y sanciones manualmente
- **Recomendación:** Borra los libros antes de importar el nuevo CSV



