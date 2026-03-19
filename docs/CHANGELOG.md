# Historial de cambios — ContaSAT

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Las versiones siguen [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.0.0] — 2026-03-19

### Nuevo
- Instalador automático `.bat` que descarga todo desde GitHub en un solo paso
- Interfaz gráfica de escritorio con PyWebView (ventana nativa, sin navegador)
- Módulo Dashboard con métricas de período: emitido, recibido, balance y CFDIs en disco
- Módulo Descarga SAT con carga de e.firma via drag & drop
- Conexión al Web Service del SAT para descarga de CFDIs emitidos y recibidos
- Lógica de rango inteligente: primera ejecución descarga desde 01-Ene; ejecuciones siguientes desde última fecha − 1 día
- Overwrite por UUID: nunca se generan duplicados
- Módulo Facturas con búsqueda y filtrado por tipo
- Módulo Historial con timeline de ejecuciones y estadísticas
- Módulo Configuración con perfil fiscal, correos y automatización mensual
- Centro de Reportes con exportación a Excel
- Notificación por correo al terminar cada descarga
- Tarea automática mensual en el Programador de tareas de Windows
- Log en tiempo real dentro de la interfaz durante la descarga
- Soporte para CFDI 3.3 y 4.0
- Archivo `historial.json` como fuente de verdad de UUIDs y fechas
- Registro de log en disco (`descarga_sat.log`)

### Arquitectura
- Backend Python expuesto como API a la GUI via `pywebview.js_api`
- Descarga del SAT en hilo separado para no bloquear la interfaz
- Comunicación bidireccional: Python llama callbacks JavaScript para actualizar progreso

---

## Próximas versiones

### [1.1.0] — Planificado

- Módulo de Conciliación completo con clasificación por categoría fiscal
- Reporte DIOT en formato `.txt` listo para importar al SAT
- Reporte de balance fiscal en PDF
- Envío automático del paquete mensual al correo del contador
- Validación de vigencia de e.firma con aviso anticipado 30 días antes

### [1.2.0] — Planificado

- Soporte para múltiples RFCs (personas físicas con varias actividades)
- Gráficas de tendencia mensual en el Dashboard
- Exportación a Google Sheets
- Versión para macOS y Linux
