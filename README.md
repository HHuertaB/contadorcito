# ContaSAT

![Version](https://img.shields.io/badge/version-1.0.0-00c27a?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4?style=flat-square&logo=windows)
![License](https://img.shields.io/badge/licencia-Personal-e8c44a?style=flat-square)

Sistema de escritorio para la descarga automática, organización y gestión de Comprobantes Fiscales Digitales (CFDI) directamente desde el Web Service del SAT México.

---

## Instalación en un solo paso

Descarga **únicamente** este archivo y ejecútalo como Administrador:

```
instalar_contasat.bat
```

El instalador descarga Python, las dependencias y todos los scripts desde este repositorio. No necesitas descargar nada más.

---

## Qué incluye

| Módulo | Descripción |
|--------|-------------|
| Dashboard | Métricas del período: emitido, recibido, balance y CFDIs en disco |
| Descarga SAT | Conexión al Web Service del SAT con e.firma via drag & drop |
| Facturas | Consulta, búsqueda y filtrado de todos los CFDIs descargados |
| Conciliación | Clasificación de facturas por categoría para declaraciones |
| Reportes | Excel, DIOT, balance fiscal y paquete para contador |
| Historial | Registro completo de sincronizaciones con estadísticas |
| Configuración | RFC, régimen fiscal, correos y automatización mensual |

---

## Arquitectura

```
contadorcito/
├── instalar_contasat.bat        ← Único archivo que el usuario descarga
├── src/
│   ├── app.py                   ← Backend Python + API PyWebView
│   ├── contasat_gui.html        ← Interfaz gráfica (HTML/CSS/JS)
│   └── instalar_dependencias.py ← Instalador de librerías
├── docs/
│   ├── INSTALL.md
│   ├── CHANGELOG.md
│   └── ContaSAT_Guia_de_Usuario.docx
├── .gitignore
└── README.md
```

---

## Cómo funciona la descarga inteligente

```
¿Primera ejecución?
  SÍ  →  01 Ene año actual  →  hoy
  NO  →  (última fecha descargada − 1 día)  →  hoy

¿CFDI ya descargado (UUID duplicado)?
  →  Overwrite. Nunca se generan duplicados.
```

---

## Requisitos

- Windows 10 / 11 (64 bits)
- Conexión a internet
- RFC activo ante el SAT
- e.firma (FIEL) vigente — archivos `.cer` y `.key`

Python 3.10+ se instala automáticamente si no está presente.

---

## Uso manual (sin instalador)

```bash
# Instalar dependencias
pip install pywebview cfdiclient openpyxl lxml schedule

# Ejecutar la aplicación
python src/app.py

# Descarga por línea de comandos (sin GUI)
python src/descarga_cfdi_sat.py --auto
```

---

## Seguridad

Los archivos de e.firma y la contraseña nunca se transmiten a ningún servidor externo distinto al del SAT. Todo el procesamiento es local.

---

## Documentación

- [Guía de instalación detallada](docs/INSTALL.md)
- [Historial de cambios](docs/CHANGELOG.md)
- [Guía de usuario completa](docs/ContaSAT_Guia_de_Usuario.docx)
