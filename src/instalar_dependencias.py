#!/usr/bin/env python3
"""
=============================================================
  INSTALADOR DE DEPENDENCIAS
  Ejecuta este script una sola vez antes de usar el sistema
=============================================================
"""
import subprocess, sys

print("📦 Instalando dependencias para descarga de CFDIs del SAT...\n")

paquetes = [
    ("cfdiclient",  "Cliente del Web Service del SAT"),
    ("openpyxl",    "Generación de reportes Excel"),
    ("lxml",        "Procesamiento de XML"),
    ("schedule",    "Automatización de tareas programadas"),
]

errores = []
for pkg, descripcion in paquetes:
    print(f"  Instalando {pkg} ({descripcion})...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg, "--upgrade", "-q"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✅ {pkg} instalado.")
    else:
        print(f"  ❌ Error con {pkg}: {result.stderr.strip()}")
        errores.append(pkg)

print()
if errores:
    print(f"⚠️  Hubo errores con: {', '.join(errores)}")
    print("   Intenta instalarlos manualmente: pip install " + " ".join(errores))
else:
    print("✅ Todas las dependencias instaladas correctamente.")
    print()
    print("Próximos pasos:")
    print("  1. Edita descarga_cfdi_sat.py y configura tu RFC, .cer, .key y contraseña")
    print("  2. Descarga manual:    python descarga_cfdi_sat.py")
    print("  3. Período específico: python descarga_cfdi_sat.py --inicio 2025-01-01 --fin 2025-01-31")
    print("  4. Modo automático:    python descarga_cfdi_sat.py --auto")
    print()
    print("  Windows: ejecuta configurar_tarea_windows.bat como Administrador")
    print("  Mac/Linux: agrega al cron: 0 8 1 * * python3 /ruta/descarga_cfdi_sat.py --auto")
