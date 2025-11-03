#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script simple para explorar la base de datos BIBLIOSENA
"""
import sqlite3
import os

DB_PATH = "bibliosena.db"

def mostrar_tablas(cursor):
    """Muestra todas las tablas disponibles"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = cursor.fetchall()
    print("\n📚 TABLAS DISPONIBLES:")
    print("-" * 50)
    for i, (tabla,) in enumerate(tablas, 1):
        print(f"{i}. {tabla}")
    return [tabla[0] for tabla in tablas]

def mostrar_contenido_tabla(cursor, nombre_tabla, limite=10):
    """Muestra el contenido de una tabla"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {nombre_tabla};")
        total = cursor.fetchone()[0]
        print(f"\n📊 Tabla: {nombre_tabla} ({total} registros)")
        print("-" * 80)
        
        cursor.execute(f"SELECT * FROM {nombre_tabla} LIMIT {limite};")
        columnas = [desc[0] for desc in cursor.description]
        
        # Imprimir encabezados
        print(" | ".join(columnas[:5]))  # Mostrar solo primeras 5 columnas
        print("-" * 80)
        
        for fila in cursor.fetchall():
            print(" | ".join(str(val)[:20] if val else "" for val in fila[:5]))  # Primeras 5 columnas, truncadas
        
        if total > limite:
            print(f"\n... (mostrando {limite} de {total} registros)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def ejecutar_consulta(cursor, query):
    """Ejecuta una consulta SQL personalizada"""
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if resultados:
            columnas = [desc[0] for desc in cursor.description]
            print("\n📋 RESULTADOS:")
            print("-" * 80)
            print(" | ".join(columnas))
            print("-" * 80)
            for fila in resultados:
                print(" | ".join(str(val)[:30] if val else "" for val in fila))
            print(f"\n✓ {len(resultados)} registro(s) encontrado(s)")
        else:
            print("✓ Consulta ejecutada (sin resultados)")
    except Exception as e:
        print(f"❌ Error: {e}")

def menu_principal():
    """Menú interactivo"""
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encuentra la base de datos: {DB_PATH}")
        print("   Asegúrate de ejecutar este script desde la carpeta BILIOSENA")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🗄️  EXPLORADOR DE BASE DE DATOS - BIBLIOSENA")
    print("=" * 80)
    
    while True:
        tablas = mostrar_tablas(cursor)
        
        print("\n" + "=" * 80)
        print("OPCIONES:")
        print("  1-9  : Ver contenido de una tabla")
        print("  q    : Ejecutar consulta SQL personalizada")
        print("  s    : Estadísticas generales")
        print("  x    : Salir")
        print("=" * 80)
        
        opcion = input("\n➜ Selecciona una opción: ").strip().lower()
        
        if opcion == 'x':
            print("\n👋 ¡Hasta luego!")
            break
        elif opcion == 's':
            print("\n📊 ESTADÍSTICAS GENERALES:")
            print("-" * 50)
            for tabla in tablas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
                count = cursor.fetchone()[0]
                print(f"  {tabla:30s} : {count:>5} registros")
        elif opcion == 'q':
            print("\n💡 Escribe tu consulta SQL (o 'cancelar' para volver):")
            query = input("SQL> ")
            if query.lower() != 'cancelar':
                ejecutar_consulta(cursor, query)
        elif opcion.isdigit() and 1 <= int(opcion) <= len(tablas):
            tabla_seleccionada = tablas[int(opcion) - 1]
            limite = input(f"\n¿Cuántos registros mostrar? (Enter para 10): ").strip()
            limite = int(limite) if limite.isdigit() else 10
            mostrar_contenido_tabla(cursor, tabla_seleccionada, limite)
        else:
            print("❌ Opción no válida")
        
        input("\nPresiona Enter para continuar...")
    
    conn.close()

if __name__ == "__main__":
    menu_principal()



