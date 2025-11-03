# 🔧 Cómo Instalar openpyxl

Si quieres importar archivos **Excel (.xlsx o .xls)**, necesitas instalar `openpyxl`.

## ⚠️ Importante

- **Para archivos CSV**: NO necesitas openpyxl, funciona directamente
- **Para archivos Excel**: SÍ necesitas openpyxl

## 📋 Instrucciones

### Opción 1: Instalar solo openpyxl

Abre una terminal/CMD en la carpeta del proyecto y ejecuta:

```bash
pip install openpyxl
```

### Opción 2: Reinstalar todas las dependencias

```bash
pip install -r requirements.txt
```

## ✅ Verificar Instalación

Para verificar que se instaló correctamente:

```bash
python -c "import openpyxl; print('✓ openpyxl instalado:', openpyxl.__version__)"
```

## 🔍 Si Sigues Teniendo Problemas

1. **Asegúrate de estar en el entorno virtual correcto** (si usas uno)
2. **Verifica que estés usando el mismo Python** que ejecuta la app
3. **Para CSV**: Simplemente guarda tu archivo Excel como CSV:
   - Excel: Archivo → Guardar como → CSV UTF-8 (delimitado por comas)

## 💡 Alternativa Rápida

Si no quieres instalar openpyxl, puedes:
1. Abrir tu archivo Excel
2. Guardarlo como CSV (Archivo → Guardar como → CSV UTF-8)
3. Importar el CSV directamente (funciona sin openpyxl)



