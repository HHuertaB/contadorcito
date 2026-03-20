# ContaSAT

![Version](https://img.shields.io/badge/version-3.7.0-00c27a?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4?style=flat-square&logo=windows)
![License](https://img.shields.io/badge/licencia-Personal-e8c44a?style=flat-square)

Sistema de escritorio para la descarga automatica, organizacion y gestion de
Comprobantes Fiscales Digitales (CFDI) directamente desde el Web Service del SAT Mexico.

---

## Instalacion en un solo paso

Descarga unicamente este archivo y ejecutalo como Administrador:

```
instalar_contasat.bat
```

El instalador descarga Python, crea un entorno virtual, instala las dependencias
y los scripts desde este repositorio. No necesitas descargar nada mas.

---

## Como funciona

Al ejecutar el acceso directo del Escritorio:

1. Se abre una terminal con ContaSAT iniciando en `http://localhost:5120`
2. El navegador (Edge o Chrome) se abre automaticamente con la aplicacion
3. Para cerrar ContaSAT, cierra la terminal

---

## Modulos

| Modulo | Descripcion |
|--------|-------------|
| Dashboard | Metricas del periodo: emitido, recibido, balance y CFDIs en disco |
| Descarga SAT | Conexion al SAT con e.firma via drag & drop |
| Facturas | Consulta, busqueda y filtrado de todos los CFDIs descargados |
| Conciliacion | Clasificacion de facturas por categoria para declaraciones |
| Reportes | Excel, DIOT y paquete para contador |
| Historial | Registro completo de sincronizaciones con estadisticas |
| Configuracion | RFC, regimen, correo SMTP y automatizacion mensual |

---

## Arquitectura

```
contadorcito/
├── instalar_contasat.bat        <- Unico archivo que el usuario descarga
├── src/
│   ├── app.py                   <- Backend Flask + API /api/*
│   ├── contasat_gui.html        <- Interfaz grafica HTML/CSS/JS
│   └── iniciar_contasat.bat     <- Lanzador con verificacion de dependencias
├── docs/
│   ├── INSTALL.md
│   ├── CHANGELOG.md
│   ├── CONTRIBUTING.md
│   └── ContaSAT_Guia_de_Usuario.docx
├── .gitignore
└── README.md
```

---

## Descarga inteligente

```
Primera ejecucion:  01 Ene del ano actual  ->  hoy
Ejecuciones siguientes: (ultima fecha - 1 dia)  ->  hoy

Rango > 3 meses:  se divide automaticamente en bloques trimestrales
                  (limite del SAT por solicitud)

Si se cierra el programa: el plan se guarda en disco y al reabrir
                          aparece opcion de continuar desde donde se quedo

CFDI duplicado:  overwrite por UUID, nunca se generan duplicados
```

---

## Notificaciones por correo

Al terminar cada descarga, ContaSAT envia automaticamente un correo con:
- Tabla resumen del periodo (total emitido, recibido, balance)
- Reporte Excel adjunto con hojas Resumen, Emitidas y Recibidas

Requiere una **contrasena de aplicacion de Gmail** (no la contrasena normal).
Se genera en myaccount.google.com/security y se configura una sola vez.

---

## Requisitos

- Windows 10 / 11 (64 bits)
- Conexion a internet
- RFC activo ante el SAT
- e.firma (FIEL) vigente con archivos .cer y .key

Python y el entorno virtual se configuran automaticamente por el instalador.

---

## Uso por linea de comandos (sin GUI)

```bash
# Activar el entorno virtual
ContaSAT\venv\Scripts\activate

# Descarga automatica (rango inteligente)
python src\app.py

# O directamente el motor de descarga
python src\descarga_cfdi_sat.py
python src\descarga_cfdi_sat.py --inicio 2025-01-01 --fin 2025-12-31
python src\descarga_cfdi_sat.py --auto
```

---

## Seguridad

Los archivos de e.firma (.cer, .key) y la contrasena nunca se transmiten
a ningún servidor externo distinto al del SAT. Todo el procesamiento es local.

La contrasena de aplicacion de Gmail se guarda en config.json en texto plano.
No es tu contrasena principal — puede revocarse en cualquier momento desde
myaccount.google.com/security sin afectar tu cuenta.

No incluyas tus archivos de e.firma ni contraseñas en este repositorio.
El .gitignore ya los excluye.

---

## Documentacion

- [Guia de instalacion](docs/INSTALL.md)
- [Historial de cambios](docs/CHANGELOG.md)
- [Como contribuir](docs/CONTRIBUTING.md)
- [Guia de usuario completa](docs/ContaSAT_Guia_de_Usuario.docx)

---

## Aviso legal

ContaSAT es una herramienta de apoyo para la gestion de CFDIs. No reemplaza
la asesoria de un contador publico certificado. Los reportes generados deben
validarse antes de presentar declaraciones ante el SAT.
