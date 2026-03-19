# Guía de Instalación — ContaSAT

## Instalación automática (recomendada)

### Paso 1 — Descargar el instalador

Descarga el archivo `instalar_contasat.bat` desde la página principal del repositorio.
Es el único archivo que necesitas.

### Paso 2 — Ejecutar como Administrador

1. Localiza el archivo descargado
2. Haz clic derecho sobre él
3. Selecciona **Ejecutar como administrador**
4. Si Windows muestra una advertencia de SmartScreen, haz clic en **Más información** y luego en **Ejecutar de todas formas**

### Paso 3 — Esperar a que termine

El instalador pasa por 7 etapas automáticamente:

| Etapa | Acción |
|-------|--------|
| 1/7 | Verifica conexión a internet y permisos |
| 2/7 | Crea carpetas en `C:\Users\TuUsuario\ContaSAT\` |
| 3/7 | Detecta Python; lo descarga e instala si no existe |
| 4/7 | Descarga los scripts desde GitHub |
| 5/7 | Instala dependencias Python |
| 6/7 | Registra la tarea mensual automática |
| 7/7 | Crea acceso directo en el Escritorio |

### Paso 4 — Configuración inicial

1. Abre el acceso directo **ContaSAT** en el Escritorio
2. Ve al módulo **Configuración** en el menú lateral
3. Escribe tu RFC y nombre completo
4. Guarda los cambios

### Paso 5 — Cargar la e.firma

1. Copia tus archivos `.cer` y `.key` a la carpeta `C:\Users\TuUsuario\ContaSAT\efirma\`
2. En el módulo **Descarga SAT**, arrastra cada archivo a su área correspondiente
3. Escribe tu contraseña de e.firma
4. Haz clic en **Validar** — el sistema confirma con el SAT

---

## Instalación manual (avanzado)

Si prefieres instalar sin el `.bat`:

```bash
# 1. Clonar el repositorio
git clone https://github.com/HHuertaB/contadorcito.git
cd contadorcito

# 2. Instalar dependencias
pip install pywebview cfdiclient openpyxl lxml schedule

# 3. Ejecutar
python src/app.py
```

---

## Verificar la instalación

Después de instalar, confirma que todo esté en orden:

**Carpetas creadas:**
```
C:\Users\TuUsuario\ContaSAT\
├── efirma\
├── contabilidad_sat\
├── logs\
└── src\
    ├── app.py
    ├── contasat_gui.html
    └── descarga_cfdi_sat.py
```

**Python disponible:**
```cmd
python --version
# Debe mostrar Python 3.10 o superior
```

**Tarea programada:**
- Abre el **Programador de tareas** de Windows
- Busca `ContaSAT_DescargaMensual`
- Debe aparecer programada para el día 1 de cada mes a las 08:00

---

## Actualizar ContaSAT

Cuando haya una nueva versión, simplemente vuelve a ejecutar `instalar_contasat.bat`. Descargará los archivos más recientes de GitHub y actualizará la instalación sin borrar tus datos ni configuración.

---

## Desinstalar

1. Elimina la tarea automática:
   ```cmd
   schtasks /Delete /TN "ContaSAT_DescargaMensual" /F
   ```
2. Elimina la carpeta `C:\Users\TuUsuario\ContaSAT\`
3. Elimina el acceso directo del Escritorio

Tus CFDIs en XML no se eliminan si haces una copia de respaldo antes.

---

## Solución de problemas frecuentes

**"Python no se reconoce como comando"**
Cierra y vuelve a abrir el Símbolo del sistema. Si persiste, reinstala Python marcando la opción *Agregar Python al PATH*.

**"No se pudo descargar desde GitHub"**
Verifica tu conexión a internet. Si tu empresa tiene un proxy corporativo, contacta a tu área de sistemas.

**"e.firma inválida"**
Confirma que los archivos `.cer` y `.key` correspondan al mismo RFC y que la contraseña sea correcta. Si tu e.firma está vencida, renuévala en el portal del SAT antes de continuar.

**La ventana de la aplicación no abre**
Ejecuta desde la terminal para ver el error:
```cmd
cd C:\Users\TuUsuario\ContaSAT
python src\app.py
```
