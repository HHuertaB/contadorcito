# Cómo contribuir a ContaSAT

Gracias por tu interés en mejorar ContaSAT. Este documento explica cómo reportar errores, proponer mejoras y contribuir código al proyecto.

---

## Tabla de contenido

- [Código de conducta](#código-de-conducta)
- [Reportar un error](#reportar-un-error)
- [Proponer una mejora](#proponer-una-mejora)
- [Configurar el entorno de desarrollo](#configurar-el-entorno-de-desarrollo)
- [Flujo de trabajo para contribuir código](#flujo-de-trabajo-para-contribuir-código)
- [Estándares de código](#estándares-de-código)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Preguntas frecuentes](#preguntas-frecuentes)

---

## Código de conducta

Este proyecto es de uso personal y colaborativo. Se espera que cualquier interacción sea respetuosa, constructiva y orientada a mejorar la herramienta. No se aceptarán contribuciones que incluyan datos fiscales reales, contraseñas ni archivos de e.firma.

---

## Reportar un error

Antes de abrir un Issue, verifica que:

1. El error no esté ya reportado en la sección [Issues](https://github.com/HHuertaB/contadorcito/issues).
2. Estás usando la versión más reciente del repositorio.
3. El error es reproducible — ocurre más de una vez en las mismas condiciones.

### Qué incluir en el reporte

Abre un Issue con la etiqueta `bug` e incluye:

- **Descripción breve** — una línea que resume el problema.
- **Pasos para reproducirlo** — secuencia exacta de acciones que generan el error.
- **Comportamiento esperado** — qué debería pasar.
- **Comportamiento actual** — qué pasa en realidad.
- **Capturas de pantalla** — si el error es visible en la interfaz.
- **Log de error** — copia el contenido relevante de `ContaSAT\contabilidad_sat\descarga_sat.log`.
- **Entorno**:
  - Versión de Windows
  - Versión de Python (`python --version`)
  - Versión de ContaSAT (ver `CHANGELOG.md`)

### Información que NUNCA debes incluir

- Tu RFC
- Contraseña de e.firma
- Archivos `.cer` o `.key`
- UUIDs reales de tus CFDIs
- Cualquier dato fiscal personal

---

## Proponer una mejora

Para proponer una nueva funcionalidad o cambio de comportamiento:

1. Abre un Issue con la etiqueta `enhancement`.
2. Describe el problema que resuelve la mejora, no solo la solución.
3. Si tienes una implementación en mente, descríbela brevemente.
4. Espera retroalimentación antes de comenzar a desarrollar — así evitamos trabajo duplicado.

### Ideas bienvenidas actualmente

- Módulo de conciliación completo con categorías fiscales
- Reporte DIOT en formato `.txt` importable al SAT
- Soporte para múltiples RFCs
- Gráficas de tendencia mensual en el Dashboard
- Versión para macOS y Linux
- Empaquetado como `.exe` con PyInstaller

---

## Configurar el entorno de desarrollo

### Requisitos

- Python 3.10 o superior
- Git
- Node.js 18+ (opcional, solo para regenerar la guía en Word)

### Clonar el repositorio

```bash
git clone https://github.com/HHuertaB/contadorcito.git
cd contadorcito
```

### Instalar dependencias

```bash
pip install pywebview cfdiclient openpyxl lxml schedule
```

### Ejecutar en modo desarrollo

```bash
python src/app.py
```

PyWebView abre la ventana directamente desde el archivo HTML. Cualquier cambio en `contasat_gui.html` requiere reiniciar la aplicación.

### Probar la GUI sin PyWebView

Abre `src/contasat_gui.html` directamente en un navegador. La GUI funciona en modo stub — todas las llamadas a la API Python devuelven respuestas simuladas, lo que permite iterar en el diseño sin ejecutar el backend completo.

### Probar la descarga sin e.firma real

Usa el parámetro `--tipo Metadata` que consume menos cuota del SAT:

```bash
python src/descarga_cfdi_sat.py --inicio 2026-01-01 --fin 2026-01-31
```

---

## Flujo de trabajo para contribuir código

### 1. Crear una rama

Usa nombres descriptivos basados en el tipo de cambio:

```bash
# Para corrección de errores
git checkout -b fix/descripcion-del-error

# Para nuevas funcionalidades
git checkout -b feat/nombre-de-la-funcionalidad

# Para documentación
git checkout -b docs/seccion-que-se-actualiza
```

### 2. Hacer los cambios

Sigue los estándares de código descritos en la siguiente sección. Haz commits pequeños y enfocados — un commit por cambio lógico.

### 3. Escribir un mensaje de commit claro

Sigue el estándar [Conventional Commits](https://www.conventionalcommits.org/es/):

```
tipo(alcance): descripción breve en imperativo

Descripción más larga si es necesaria. Explica el por qué,
no el qué — el código ya muestra el qué.

Fixes #12
```

Tipos permitidos:

| Tipo | Cuándo usarlo |
|------|---------------|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de error |
| `docs` | Solo documentación |
| `style` | Formato, espacios (sin cambio funcional) |
| `refactor` | Refactorización sin cambio de comportamiento |
| `test` | Agregar o corregir pruebas |
| `chore` | Tareas de mantenimiento (dependencias, CI) |

Ejemplos:

```
feat(descarga): agregar soporte para descarga de nóminas (CFDI tipo N)
fix(fiel): corregir error al cargar .cer con caracteres especiales en la ruta
docs(install): agregar instrucciones para macOS
```

### 4. Abrir un Pull Request

1. Sube tu rama: `git push origin feat/tu-funcionalidad`
2. Abre un Pull Request desde GitHub apuntando a la rama `main`
3. Completa la descripción del PR:
   - Qué cambia y por qué
   - Cómo probarlo
   - Capturas de pantalla si hay cambios visuales
   - Issue relacionado con `Closes #N` si aplica

---

## Estándares de código

### Python (`app.py`, `descarga_cfdi_sat.py`)

- Seguir [PEP 8](https://peps.python.org/pep-0008/)
- Nombres de variables y funciones en `snake_case`
- Nombres de clases en `PascalCase`
- Docstrings en español para métodos públicos
- Evitar líneas de más de 100 caracteres
- No incluir credenciales, RFCs reales ni datos personales en el código

```python
# Correcto
def calcular_rango(fecha_ini: datetime.date, fecha_fin: datetime.date) -> dict:
    """Calcula el rango de descarga según la lógica de incrementos."""
    ...

# Incorrecto
def CalcRng(fi, ff):
    ...
```

### HTML / CSS / JavaScript (`contasat_gui.html`)

- Todo el código del frontend va en un único archivo HTML autocontenido
- Variables CSS en `:root` para todos los colores y tokens de diseño
- Funciones JavaScript en `camelCase`
- Comentarios en español
- La comunicación con Python siempre pasa por la función `api()` — nunca llamar `window.pywebview.api` directamente en el resto del código

```javascript
// Correcto — siempre usar el wrapper api()
const resultado = await api('get_config');

// Incorrecto — acoplamiento directo con pywebview
const resultado = await window.pywebview.api.get_config();
```

### Markdown (documentación)

- Títulos en español
- Tablas para comparaciones o listas estructuradas
- Bloques de código con el lenguaje especificado
- Sin emoticonos en documentación técnica
- Máximo 100 caracteres por línea en párrafos

---

## Estructura del proyecto

```
contadorcito/
├── instalar_contasat.bat   ← Instalador Windows. Descarga todo de GitHub.
│
├── src/
│   ├── app.py              ← Punto de entrada. Backend Python + arranque PyWebView.
│   │                          Contiene la clase ContaSATAPI con todos los métodos
│   │                          expuestos a JavaScript.
│   │
│   ├── contasat_gui.html   ← Frontend completo. HTML + CSS + JavaScript en un
│   │                          solo archivo. Se comunica con app.py via api().
│   │
│   ├── descarga_cfdi_sat.py ← Motor de descarga SAT. Puede usarse de forma
│   │                           independiente por línea de comandos.
│   │
│   └── instalar_dependencias.py ← Instalador de librerías Python.
│
├── docs/
│   ├── INSTALL.md          ← Guía de instalación paso a paso
│   ├── CHANGELOG.md        ← Historial de versiones
│   ├── CONTRIBUTING.md     ← Este archivo
│   └── ContaSAT_Guia_de_Usuario.docx ← Guía completa en Word
│
├── .gitignore              ← Excluye e.firma, datos personales y temporales
└── README.md               ← Página principal del repositorio
```

### Dónde agregar cada tipo de cambio

| Cambio | Archivo(s) a modificar |
|--------|------------------------|
| Nueva pantalla o módulo en la GUI | `contasat_gui.html` |
| Nuevo endpoint de la API Python | `app.py` — clase `ContaSATAPI` |
| Nueva lógica de descarga SAT | `descarga_cfdi_sat.py` |
| Nueva opción en el instalador | `instalar_contasat.bat` |
| Documentación de uso | `docs/INSTALL.md` o `README.md` |
| Historial de cambios | `docs/CHANGELOG.md` |

---

## Preguntas frecuentes

**¿Puedo contribuir si no sé Python?**
Sí. La documentación, los estilos CSS de la GUI y las traducciones son contribuciones valiosas que no requieren Python.

**¿Cómo pruebo que mi cambio no rompe nada?**
Ejecuta `python src/app.py` y verifica que la aplicación arranca. Abre `contasat_gui.html` en el navegador y navega por todos los módulos para confirmar que la interfaz no tiene errores visuales.

**¿Se aceptan contribuciones para otras plataformas (Mac, Linux)?**
Sí, pero la prioridad actual es Windows. Los PRs para otras plataformas son bienvenidos siempre que no rompan la compatibilidad con Windows.

**¿Puedo agregar soporte para otro sistema de facturación electrónica (Guatemala, Colombia, etc.)?**
Es una mejora interesante. Abre un Issue primero para discutir la arquitectura antes de implementar.
