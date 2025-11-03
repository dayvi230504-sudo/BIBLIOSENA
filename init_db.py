#!/usr/bin/env python
"""
Script para inicializar la base de datos en producción (PostgreSQL)
Ejecutar una sola vez al desplegar por primera vez
"""
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, Base, engine

def init_database():
    """Crear todas las tablas en la base de datos"""
    with app.app_context():
        try:
            # Crear todas las tablas
            Base.metadata.create_all(bind=engine)
            print("✅ Tablas creadas exitosamente")
            
            # Ejecutar migraciones
            from app import migrar_base_datos
            migrar_base_datos()
            
            print("✅ Base de datos inicializada correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al inicializar base de datos: {e}")
            return False

if __name__ == "__main__":
    init_database()

