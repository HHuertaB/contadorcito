# ContaSAT — Gestión de CFDIs del SAT México

Sistema de escritorio para la descarga automática, organización y gestión de Comprobantes Fiscales Digitales por Internet (CFDI) directamente desde el Web Service del SAT.

---

## Instalación

Solo descarga un archivo y ejecútalo como Administrador:

1. Descarga [`instalar_contasat.bat`](instalar_contasat.bat)
2. Haz clic derecho → **Ejecutar como administrador**
3. El instalador descarga Python, las dependencias y los scripts automáticamente

El resto lo hace solo. No necesitas descargar ningún otro archivo manualmente.

---

## Qué hace el instalador

| Etapa | Acción |
|-------|--------|
| 1 | Verifica conexión a internet y permisos de administrador |
| 2 | Crea la estructura de carpetas en `C:\Users\TuUsuario\ContaSAT\` |
| 3 | Detecta Python; si no existe, lo descarga e instala (Python 3.12) |
| 4 | Descarga los scripts desde este repositorio |
| 5 | Instala las dependencias Python (`cfdiclient`, `openpyxl`, `lxml`, `schedule`) |
| 6 | Registra la tarea mensual automática en el Programador de tareas de Windows |
| 7 | Crea acceso directo en el Escritorio |

---

## Funcionalidades

- **Descarga automática mensual** de CFDIs emitidos y recibidos via Web Service del SAT
- **Rango inteligente**: primera ejecución descarga desde el 1 de enero; ejecuciones siguientes descargan desde la última fecha registrada
- **Overwrite por UUID**: nunca genera duplicados; sobreescribe si el CFDI ya existe
- **Interfaz gráfica** con Dashboard, módulo de facturas, conciliación y reportes
- **Notificación por correo** al terminar cada descarga con reporte Excel adjunto
- **Reportes**: relación de CFDIs, DIOT, balance fiscal, top proveedores

---

## Requisitos

- Windows 10 / 11 (64 bits)
- Conexión a internet (solo durante la instalación y las descargas del SAT)
- RFC activo ante el SAT
- e.firma (FIEL) vigente con archivos `.cer` y `.key`

Python se instala automáticamente si no está presente.

---

## Estructura del repositorio

```
contadorcito/
├── instalar_contasat.bat        # Instalador — único archivo que el usuario descarga
├── src/
│   ├── descarga_cfdi_sat.py     # Motor principal de descarga
│   ├── contasat_gui.html        # Interfaz gráfica
│   └── instalar_dependencias.py # Instalador de librerías Python
├── docs/
│   └── ContaSAT_Guia_de_Usuario.docx
└── README.md
```

---

## Uso después de instalar

```bash
# Descarga automática (rango inteligente)
python descarga_cfdi_sat.py

# Período específico
python descarga_cfdi_sat.py --inicio 2025-01-01 --fin 2025-12-31

# Modo scheduler (corre en segundo plano)
python descarga_cfdi_sat.py --auto
```

---

## Seguridad

Los archivos de e.firma (`.cer`, `.key`) y la contraseña **nunca se transmiten** a ningún servidor externo distinto al del SAT. Todo el procesamiento es local en tu equipo.

No incluyas tus archivos de e.firma ni tu contraseña en este repositorio.

---

## Licencia

Uso personal. Consulta a un contador público certificado antes de usar los reportes generados en declaraciones fiscales.
