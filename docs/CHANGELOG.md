# Historial de cambios — ContaSAT

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Las versiones siguen [Semantic Versioning](https://semver.org/lang/es/).

---

## [3.7.0] — 2026-03-19

### Arquitectura
- Migrado de PyWebView a Flask + navegador del sistema (Edge/Chrome)
  - Elimina dependencia de pythonnet, NuGet y compilacion de .NET
  - La GUI se sirve en localhost:5120 y se abre automaticamente
  - Comunicacion Python <-> GUI via fetch(/api/...) en lugar de pywebview.api
- Migrado de cfdiclient a satcfdi para la comunicacion con el SAT
  - cfdiclient tenia API inestable que rompia entre versiones
  - satcfdi usa metodos claros: recover_comprobante_received_request,
    recover_comprobante_emitted_request, recover_comprobante_status,
    recover_comprobante_download
- Entorno virtual (venv) obligatorio — aisla completamente las dependencias
  del sistema operativo y elimina conflictos de versiones de Python

### Nuevo
- Division automatica de rangos en bloques de 3 meses (limite del SAT)
  - Una solicitud de año completo se divide en 4 bloques secuenciales
  - El log muestra el avance: [1/8], [2/8], etc.
- Plan de descarga persistente (plan_descarga.json)
  - Si se cierra el programa durante una descarga, al reabrir aparece
    un banner para continuar desde donde se quedo
  - Cada bloque tiene estado: pendiente, en_proceso, completado, error
- Solicitudes pendientes individuales (solicitudes_pendientes.json)
  - Guarda el ID de cada solicitud al crearla
  - Al reabrir la app muestra banner con opcion de reanudar
- Envio de correo por SMTP al terminar cada descarga
  - Usa contraseña de aplicacion de Gmail (no la contraseña normal)
  - Correo HTML con tabla resumen y Excel adjunto
  - Endpoint /api/correo/probar para validar configuracion
  - La contraseña se guarda en config.json y no se vuelve a pedir
- GUI completamente reconstruida sin datos de demostracion
  - Un solo archivo HTML valido (1 html, 1 body, 1 script)
  - Todos los datos vienen de /api/* en tiempo real
  - Estado inicial limpio hasta que se configure el RFC y se descarguen CFDIs
- Parametro estado_comprobante=VIGENTE en solicitudes al SAT
  - Resuelve el error 301 "No se permite descarga de xml cancelados"
- Campo smtp_password en configuracion con persistencia automatica

### Corregido
- Error 301 del SAT al solicitar CFDIs recibidos
- Interfaz duplicada por multiples inyecciones de bridge en el HTML
- Datos hardcodeados visibles sin haber configurado el sistema
- Metodo recover_comprobante_iwait inexistente en satcfdi instalado
- Instalador .bat con caracteres UTF-8 que corrompian etiquetas goto
- Acceso directo que cerraba la terminal sin mostrar el error

---

## [1.0.0] — 2026-03-19 (version inicial)

### Nuevo
- Instalador automatico .bat que descarga todo desde GitHub en un solo paso
- Interfaz grafica con Dashboard, Descarga SAT, Facturas, Conciliacion,
  Reportes, Historial y Configuracion
- Descarga de CFDIs emitidos y recibidos via Web Service del SAT
- Rango inteligente: primera ejecucion desde 01-Ene; siguientes desde
  ultima fecha menos 1 dia
- Overwrite por UUID: nunca se generan duplicados
- Carga de e.firma con drag & drop (.cer y .key)
- Rutas de e.firma recordadas entre sesiones (solo pide contraseña)
- Reporte Excel con hojas Resumen, Emitidas y Recibidas
- Tarea automatica mensual en Programador de tareas de Windows
- Historial de descargas con timeline de ejecuciones
- Soporte para CFDI 3.3 y 4.0
- Documentacion: README.md, INSTALL.md, CHANGELOG.md, CONTRIBUTING.md
  y Guia de Usuario en Word

---

## Proximas versiones

### [3.8.0] — Planificado
- Modulo de conciliacion con clasificacion por categoria fiscal
- Reporte DIOT en formato .txt importable al SAT
- Envio del paquete mensual al contador por correo

### [4.0.0] — Planificado
- Soporte para multiples RFCs
- Graficas de tendencia mensual en el Dashboard
- Version para macOS y Linux
