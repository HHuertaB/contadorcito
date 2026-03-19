"""
ContaSAT — app.py
Backend principal. Expone una API JavaScript a la GUI via PyWebView.
Ejecutar: python app.py
"""

import base64
import datetime
import json
import logging
import os
import sys
import threading
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Auto-instalar dependencias ───────────────────────────────
def _pip(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

for _p in ["webview", "cfdiclient", "openpyxl", "lxml", "schedule"]:
    try:
        __import__(_p if _p != "webview" else "webview")
    except ImportError:
        print(f"Instalando {_p}...")
        _pip("pywebview" if _p == "webview" else _p)

import webview
from cfdiclient import (
    Autenticacion, DescargaMasiva, Fiel,
    SolicitaDescarga, VerificaSolicitudDescarga,
)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# ── Configuración de rutas ────────────────────────────────────
BASE_DIR  = Path(__file__).parent
GUI_FILE  = BASE_DIR / "contasat_gui.html"
DATA_DIR  = BASE_DIR / "contabilidad_sat"
HIST_FILE = BASE_DIR / "contabilidad_sat" / "historial.json"
LOG_FILE  = BASE_DIR / "contabilidad_sat" / "descarga_sat.log"
CFG_FILE  = BASE_DIR / "config.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("contasat")

# ── Configuración por defecto ─────────────────────────────────
CFG_DEFAULT = {
    "rfc": "",
    "fiel_cer": "",         # ruta completa al .cer (no es dato sensible)
    "fiel_key": "",         # ruta completa al .key (no es dato sensible)
    "fiel_cer_nombre": "",  # nombre del archivo, para mostrar en la GUI
    "fiel_key_nombre": "",  # nombre del archivo, para mostrar en la GUI
    # fiel_password NUNCA se guarda en disco
    "notif_email": "",
    "notif_cc": "",
    "dia_auto": 1,
    "hora_auto": "08:00",
    "carpeta": str(DATA_DIR),
    "nombre": "",
    "regimen": "",
}


def _load_cfg() -> dict:
    if CFG_FILE.exists():
        try:
            return {**CFG_DEFAULT, **json.loads(CFG_FILE.read_text("utf-8"))}
        except Exception:
            pass
    return dict(CFG_DEFAULT)


def _save_cfg(cfg: dict):
    CFG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")


def _load_hist() -> dict:
    if HIST_FILE.exists():
        try:
            return json.loads(HIST_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {"primera_ejecucion": True, "ultima_fecha": None,
            "uuids": [], "ejecuciones": []}


def _save_hist(h: dict):
    HIST_FILE.write_text(json.dumps(h, indent=2, ensure_ascii=False, default=str), "utf-8")


# ── Parseo CFDI ───────────────────────────────────────────────
NS = {
    "cfdi":  "http://www.sat.gob.mx/cfd/4",
    "cfdi3": "http://www.sat.gob.mx/cfd/3",
    "tfd":   "http://www.sat.gob.mx/TimbreFiscalDigital",
}

def _parsear(ruta: Path, tipo: str) -> dict:
    try:
        root = ET.parse(ruta).getroot()
        def nodo(tag):
            return root.find(f"cfdi:{tag}", NS) or root.find(f"cfdi3:{tag}", NS)
        def a(el, attr): return el.get(attr, "") if el is not None else ""
        emisor   = nodo("Emisor")
        receptor = nodo("Receptor")
        tfd      = root.find(".//tfd:TimbreFiscalDigital", NS)
        concepto = (root.find("cfdi:Conceptos/cfdi:Concepto", NS)
                    or root.find("cfdi3:Conceptos/cfdi3:Concepto", NS))
        fecha = root.get("Fecha", "")
        try: total = float(root.get("Total", 0))
        except: total = 0.0
        return {
            "tipo":     tipo,
            "uuid":     a(tfd, "UUID"),
            "fecha":    fecha[:10],
            "serie":    root.get("Serie", ""),
            "folio":    root.get("Folio", ""),
            "rfc_emisor":      a(emisor,   "Rfc"),
            "nombre_emisor":   a(emisor,   "Nombre"),
            "rfc_receptor":    a(receptor, "Rfc"),
            "nombre_receptor": a(receptor, "Nombre"),
            "uso_cfdi":        a(receptor, "UsoCFDI"),
            "descripcion":     a(concepto, "Descripcion"),
            "subtotal":  root.get("SubTotal", ""),
            "total":     total,
            "moneda":    root.get("Moneda", "MXN"),
            "tipo_comp": root.get("TipoDeComprobante", ""),
            "metodo_pago": root.get("MetodoPago", ""),
            "forma_pago":  root.get("FormaPago", ""),
            "archivo":   ruta.name,
        }
    except Exception as e:
        return {"tipo": tipo, "archivo": ruta.name, "error": str(e), "total": 0}


# ═══════════════════════════════════════════════════════════════
#  API  —  métodos expuestos a JavaScript via window.pywebview.api
# ═══════════════════════════════════════════════════════════════

class ContaSATAPI:
    """
    Todos los métodos públicos de esta clase son accesibles desde
    JavaScript como:  await window.pywebview.api.nombre_metodo(args)
    """

    def __init__(self):
        self._window = None          # se asigna después de crear la ventana
        self._fiel   = None          # FIEL cargada en memoria
        self._log_cb = []            # callbacks de log para la GUI

    # ── Utilidad: enviar log a la GUI ─────────────────────────
    def _emit(self, msg: str, level: str = "info"):
        log.info(msg)
        if self._window:
            # Escapa comillas para no romper JS
            safe = msg.replace("\\", "\\\\").replace("'", "\\'")
            self._window.evaluate_js(
                f"window.contasat && window.contasat.addLog('{safe}', '{level}')"
            )

    def _emit_progress(self, pct: int):
        if self._window:
            self._window.evaluate_js(
                f"window.contasat && window.contasat.setProgress({pct})"
            )

    def _emit_event(self, event: str, data: dict = None):
        payload = json.dumps(data or {})
        if self._window:
            self._window.evaluate_js(
                f"window.contasat && window.contasat.onEvent('{event}', {payload})"
            )

    # ─────────────────────────────────────────────────────────
    #  CONFIGURACIÓN
    # ─────────────────────────────────────────────────────────

    def get_config(self) -> dict:
        """Devuelve la configuración actual."""
        return _load_cfg()

    def save_config(self, cfg: dict) -> dict:
        """Guarda la configuración. Devuelve {ok, msg}."""
        try:
            current = _load_cfg()
            current.update(cfg)
            # No guardar contraseña en texto plano si está vacía
            _save_cfg(current)
            return {"ok": True, "msg": "Configuración guardada."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ─────────────────────────────────────────────────────────
    #  e.FIRMA
    # ─────────────────────────────────────────────────────────

    def cargar_fiel(self, cer_b64: str, key_b64: str, password: str,
                    cer_nombre: str = "", key_nombre: str = "",
                    cer_ruta: str = "", key_ruta: str = "") -> dict:
        """
        Carga la e.firma en memoria y valida contra el SAT.

        Acepta dos modos:
        - cer_b64 / key_b64: archivos enviados como base64 desde el drag & drop de la GUI.
        - cer_ruta / key_ruta: rutas absolutas en disco (cuando el usuario ya las tenía guardadas).

        Las rutas (no la contraseña) se guardan en config.json para
        precargar la GUI en la próxima sesión.
        """
        try:
            # Modo ruta en disco: leer directamente del archivo
            if cer_ruta and key_ruta and not cer_b64:
                cer_path = Path(cer_ruta)
                key_path = Path(key_ruta)
                if not cer_path.exists():
                    return {"ok": False, "msg": f"No se encontró el archivo: {cer_path.name}"}
                if not key_path.exists():
                    return {"ok": False, "msg": f"No se encontró el archivo: {key_path.name}"}
                cer = cer_path.read_bytes()
                key = key_path.read_bytes()
                cer_nombre = cer_nombre or cer_path.name
                key_nombre = key_nombre or key_path.name
            else:
                # Modo base64 desde la GUI (drag & drop o selector de archivo)
                if not cer_b64 or not key_b64:
                    return {"ok": False, "msg": "Carga los archivos .cer y .key primero."}
                cer = base64.b64decode(cer_b64)
                key = base64.b64decode(key_b64)

            self._fiel = Fiel(cer, key, password)

            # Validar con el SAT obteniendo un token de prueba
            token = Autenticacion(self._fiel).obtener_token()
            if not token:
                self._fiel = None
                return {"ok": False, "msg": "e.firma inválida o contraseña incorrecta."}

            # Guardar rutas en config (nunca la contraseña)
            cfg = _load_cfg()
            if cer_ruta: cfg["fiel_cer"] = cer_ruta
            if key_ruta: cfg["fiel_key"] = key_ruta
            cfg["fiel_cer_nombre"] = cer_nombre
            cfg["fiel_key_nombre"] = key_nombre
            _save_cfg(cfg)

            return {
                "ok":         True,
                "msg":        "e.firma válida. Token obtenido del SAT.",
                "cer_nombre": cer_nombre,
                "key_nombre": key_nombre,
            }
        except Exception as e:
            self._fiel = None
            return {"ok": False, "msg": f"Error al cargar e.firma: {str(e)}"}

    def get_fiel_status(self) -> dict:
        """Devuelve si la FIEL está cargada y los nombres de archivo recordados."""
        cfg = _load_cfg()
        return {
            "cargada":     self._fiel is not None,
            "cer_nombre":  cfg.get("fiel_cer_nombre", ""),
            "key_nombre":  cfg.get("fiel_key_nombre", ""),
            "cer_ruta":    cfg.get("fiel_cer", ""),
            "key_ruta":    cfg.get("fiel_key", ""),
            "tiene_rutas": bool(cfg.get("fiel_cer") and cfg.get("fiel_key")),
        }

    def cargar_fiel_desde_rutas_guardadas(self, password: str) -> dict:
        """
        Shortcut para cuando la GUI ya tiene las rutas guardadas.
        El usuario solo introduce la contraseña y se llama este método.
        """
        cfg = _load_cfg()
        cer_ruta = cfg.get("fiel_cer", "")
        key_ruta = cfg.get("fiel_key", "")
        if not cer_ruta or not key_ruta:
            return {"ok": False, "msg": "No hay rutas de e.firma guardadas. Carga los archivos manualmente."}
        return self.cargar_fiel(
            cer_b64="", key_b64="", password=password,
            cer_ruta=cer_ruta, key_ruta=key_ruta,
        )

    # ─────────────────────────────────────────────────────────
    #  HISTORIAL Y RANGO INTELIGENTE
    # ─────────────────────────────────────────────────────────

    def get_rango_automatico(self) -> dict:
        """Calcula el rango de descarga según la lógica inteligente."""
        h   = _load_hist()
        hoy = datetime.date.today()
        if h["primera_ejecucion"] or not h["ultima_fecha"]:
            ini = datetime.date(hoy.year, 1, 1)
            modo = "primera"
        else:
            ultima = datetime.date.fromisoformat(h["ultima_fecha"])
            ini    = ultima - datetime.timedelta(days=1)
            modo   = "incremental"
        return {
            "inicio": str(ini),
            "fin":    str(hoy),
            "modo":   modo,
            "primera_ejecucion": h["primera_ejecucion"],
        }

    def get_historial(self) -> dict:
        return _load_hist()

    def limpiar_historial(self) -> dict:
        try:
            h = {"primera_ejecucion": True, "ultima_fecha": None,
                 "uuids": [], "ejecuciones": []}
            _save_hist(h)
            return {"ok": True, "msg": "Historial limpiado."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ─────────────────────────────────────────────────────────
    #  DESCARGA SAT  (corre en hilo separado para no bloquear GUI)
    # ─────────────────────────────────────────────────────────

    def iniciar_descarga(self, inicio: str, fin: str, tipo_cfdi: str = "ambas") -> dict:
        """
        Inicia la descarga en un hilo separado.
        La GUI recibe actualizaciones via window.contasat.addLog()
        y window.contasat.setProgress().
        """
        if not self._fiel:
            return {"ok": False, "msg": "Carga y valida tu e.firma primero."}
        cfg = _load_cfg()
        if not cfg.get("rfc"):
            return {"ok": False, "msg": "Configura tu RFC primero."}

        t = threading.Thread(
            target=self._descarga_worker,
            args=(inicio, fin, tipo_cfdi, cfg),
            daemon=True,
        )
        t.start()
        return {"ok": True, "msg": "Descarga iniciada en segundo plano."}

    def _descarga_worker(self, inicio: str, fin: str, tipo_cfdi: str, cfg: dict):
        rfc      = cfg["rfc"]
        hist     = _load_hist()
        uuids    = set(hist.get("uuids", []))
        fecha_ini = datetime.date.fromisoformat(inicio)
        fecha_fin = datetime.date.fromisoformat(fin)
        hoy_str   = str(datetime.date.today())

        todos    = []
        nuevos   = overwr = 0
        tipos    = []
        if tipo_cfdi in ("ambas", "recibidas"): tipos.append("recibidas")
        if tipo_cfdi in ("ambas", "emitidas"):  tipos.append("emitidas")

        total_pasos = len(tipos) * 4   # solicitar, verificar, descargar, extraer
        paso = 0

        try:
            for tipo in tipos:
                label = tipo.upper()

                # 1. Solicitar
                self._emit(f"Solicitando CFDIs {label} {fecha_ini} → {fecha_fin}...", "info")
                token = Autenticacion(self._fiel).obtener_token()
                desc  = SolicitaDescarga(self._fiel)
                kwargs = dict(token=token, rfc_solicitante=rfc,
                              fecha_inicial=fecha_ini, fecha_final=fecha_fin,
                              tipo_solicitud="CFDI")
                if tipo == "recibidas": kwargs["rfc_receptor"] = rfc
                else:                   kwargs["rfc_emisor"]   = rfc
                resp   = desc.solicitar_descarga(**kwargs)
                id_sol = resp.get("IdSolicitud") or resp.get("id_solicitud")
                if not id_sol:
                    self._emit(f"SAT no devolvió ID para {label}: {resp}", "error")
                    continue
                self._emit(f"ID solicitud: {id_sol}", "ok")
                paso += 1; self._emit_progress(int(paso / total_pasos * 90))

                # 2. Verificar
                verif    = VerificaSolicitudDescarga(self._fiel)
                paquetes = []
                for intento in range(200):
                    token2   = Autenticacion(self._fiel).obtener_token()
                    res      = verif.verificar_descarga(token2, rfc, id_sol)
                    estado   = str(res.get("EstadoSolicitud", ""))
                    paquetes = res.get("IdsPaquetes", [])
                    self._emit(f"[{intento+1}] Estado SAT: {estado} | Paquetes: {len(paquetes)}", "info")
                    if   estado == "3": break
                    elif estado == "5":
                        self._emit(f"Sin CFDIs {label} en el período.", "warn")
                        paquetes = []; break
                    elif estado in ["1","2"]:
                        time.sleep(90)
                    else:
                        self._emit(f"Error SAT estado={estado}", "error"); break
                paso += 1; self._emit_progress(int(paso / total_pasos * 90))

                # 3. Descargar ZIPs
                descm = DescargaMasiva(self._fiel)
                carp_base = DATA_DIR / str(fecha_ini.year) / f"{fecha_ini.month:02d}"
                carp_zip  = carp_base / tipo / "zips"
                carp_xml  = carp_base / tipo / "xml"
                carp_zip.mkdir(parents=True, exist_ok=True)
                carp_xml.mkdir(parents=True, exist_ok=True)

                zips = []
                for i, pkg_id in enumerate(paquetes):
                    token3 = Autenticacion(self._fiel).obtener_token()
                    r      = descm.descargar_paquete(token3, rfc, pkg_id)
                    b64    = r.get("Paquete") or r.get("paquete")
                    if not b64:
                        self._emit(f"Paquete vacío: {pkg_id}", "warn"); continue
                    ruta = carp_zip / f"{pkg_id}.zip"
                    ruta.write_bytes(base64.b64decode(b64))
                    zips.append(ruta)
                    self._emit(f"Paquete {i+1}/{len(paquetes)} descargado", "ok")
                paso += 1; self._emit_progress(int(paso / total_pasos * 90))

                # 4. Extraer XMLs con overwrite por UUID
                tipo_label = "Emitida" if tipo == "emitidas" else "Recibida"
                for ruta_zip in zips:
                    with zipfile.ZipFile(ruta_zip) as z:
                        for nombre in [n for n in z.namelist() if n.lower().endswith(".xml")]:
                            contenido = z.read(nombre)
                            ruta_xml  = carp_xml / nombre
                            ruta_xml.write_bytes(contenido)
                            cfdi = _parsear(ruta_xml, tipo_label)
                            uuid = cfdi.get("uuid", "")
                            if uuid:
                                if uuid in uuids:
                                    overwr += 1
                                else:
                                    uuids.add(uuid)
                                    nuevos += 1
                            todos.append(cfdi)
                self._emit(f"{label}: {len(todos)} CFDIs | {nuevos} nuevos | {overwr} overwrite", "ok")
                paso += 1; self._emit_progress(int(paso / total_pasos * 90))

            # Reporte Excel
            if todos:
                self._emit("Generando reporte Excel...", "info")
                self._generar_excel(todos, carp_base / "reportes", fecha_ini, fecha_fin)

            # Actualizar historial
            hist["primera_ejecucion"] = False
            hist["ultima_fecha"]      = str(fecha_fin)
            hist["uuids"]             = list(uuids)
            hist["ejecuciones"].append({
                "fecha":   hoy_str,
                "inicio":  str(fecha_ini),
                "fin":     str(fecha_fin),
                "total":   len(todos),
                "nuevos":  nuevos,
                "overwrite": overwr,
            })
            _save_hist(hist)

            self._emit_progress(100)
            self._emit(f"COMPLETADO — {len(todos)} CFDIs | {nuevos} nuevos | {overwr} overwrite", "ok")
            self._emit_event("descarga_completada", {
                "total": len(todos), "nuevos": nuevos, "overwrite": overwr,
            })

        except Exception as e:
            self._emit(f"Error inesperado: {e}", "error")
            self._emit_event("descarga_error", {"msg": str(e)})

    # ─────────────────────────────────────────────────────────
    #  FACTURAS  (leer XMLs del disco)
    # ─────────────────────────────────────────────────────────

    def get_facturas(self, anio: int = None, mes: int = None,
                     tipo: str = "todas") -> dict:
        """Devuelve lista de CFDIs parseados desde el disco."""
        try:
            resultados = []
            base = DATA_DIR
            for xml in base.rglob("*.xml"):
                partes = xml.parts
                # Determinar tipo por carpeta padre
                if "emitidas" in partes:  t = "Emitida"
                elif "recibidas" in partes: t = "Recibida"
                else: t = "Desconocida"

                if tipo == "emitidas"  and t != "Emitida":  continue
                if tipo == "recibidas" and t != "Recibida": continue

                cfdi = _parsear(xml, t)
                if anio and cfdi.get("fecha", "")[:4] != str(anio): continue
                if mes  and cfdi.get("fecha", "")[5:7] != f"{mes:02d}": continue
                resultados.append(cfdi)

            return {"ok": True, "data": resultados, "total": len(resultados)}
        except Exception as e:
            return {"ok": False, "msg": str(e), "data": []}

    def get_dashboard_stats(self) -> dict:
        """Métricas para el dashboard."""
        try:
            result = self.get_facturas()
            if not result["ok"]: return {}
            facturas = result["data"]
            emitidas  = [f for f in facturas if f.get("tipo") == "Emitida"  and "error" not in f]
            recibidas = [f for f in facturas if f.get("tipo") == "Recibida" and "error" not in f]
            total_e   = sum(f.get("total", 0) for f in emitidas)
            total_r   = sum(f.get("total", 0) for f in recibidas)
            hist      = _load_hist()
            return {
                "total_emitidas":  len(emitidas),
                "total_recibidas": len(recibidas),
                "monto_emitido":   round(total_e, 2),
                "monto_recibido":  round(total_r, 2),
                "balance":         round(total_e - total_r, 2),
                "ultima_descarga": hist.get("ultima_fecha", "Sin descargas"),
                "total_uuids":     len(hist.get("uuids", [])),
            }
        except Exception as e:
            return {"error": str(e)}

    # ─────────────────────────────────────────────────────────
    #  REPORTE EXCEL
    # ─────────────────────────────────────────────────────────

    def _generar_excel(self, datos, carpeta: Path,
                       fecha_ini: datetime.date, fecha_fin: datetime.date):
        carpeta.mkdir(parents=True, exist_ok=True)
        wb = openpyxl.Workbook()

        fill_h = PatternFill("solid", fgColor="1F3864")
        font_h = Font(color="FFFFFF", bold=True)

        emitidas  = [d for d in datos if d.get("tipo") == "Emitida"  and "error" not in d]
        recibidas = [d for d in datos if d.get("tipo") == "Recibida" and "error" not in d]

        def _suma(lst): return round(sum(d.get("total", 0) for d in lst), 2)

        # Hoja resumen
        ws = wb.active; ws.title = "Resumen"
        for r, (k, v) in enumerate([
            ("Período",             f"{fecha_ini} → {fecha_fin}"),
            ("Facturas emitidas",   len(emitidas)),
            ("Total emitido MXN",   _suma(emitidas)),
            ("Facturas recibidas",  len(recibidas)),
            ("Total recibido MXN",  _suma(recibidas)),
            ("Balance",             _suma(emitidas) - _suma(recibidas)),
        ], 1):
            ws.cell(r, 1, k).font = Font(bold=True)
            ws.cell(r, 2, v)

        COLS = ["tipo","uuid","fecha","rfc_emisor","nombre_emisor",
                "rfc_receptor","nombre_receptor","descripcion",
                "subtotal","total","moneda","tipo_comp","archivo"]

        for nombre_hoja, filas in [("Emitidas", emitidas), ("Recibidas", recibidas)]:
            wsd = wb.create_sheet(nombre_hoja)
            for c, col in enumerate(COLS, 1):
                cell = wsd.cell(1, c, col.replace("_", " ").title())
                cell.fill = fill_h; cell.font = font_h
            for r, d in enumerate(filas, 2):
                for c, col in enumerate(COLS, 1):
                    wsd.cell(r, c, d.get(col, ""))
            wsd.auto_filter.ref = wsd.dimensions

        nombre = f"CFDIs_{fecha_ini}_{fecha_fin}.xlsx"
        ruta   = carpeta / nombre
        wb.save(ruta)
        self._emit(f"Excel guardado: {ruta}", "ok")
        return str(ruta)

    def generar_reporte(self, tipo: str = "excel") -> dict:
        """Genera reporte desde la GUI bajo demanda."""
        try:
            result = self.get_facturas()
            if not result["ok"]: return result
            datos = result["data"]
            hoy   = datetime.date.today()
            ruta  = self._generar_excel(
                datos,
                DATA_DIR / "reportes",
                datetime.date(hoy.year, 1, 1), hoy
            )
            return {"ok": True, "msg": f"Reporte generado: {ruta}", "ruta": ruta}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def abrir_carpeta(self) -> dict:
        """Abre el explorador de Windows en la carpeta de datos."""
        try:
            os.startfile(str(DATA_DIR))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def get_log_reciente(self) -> dict:
        """Devuelve las últimas 100 líneas del log."""
        try:
            if LOG_FILE.exists():
                lines = LOG_FILE.read_text("utf-8").splitlines()
                return {"ok": True, "lines": lines[-100:]}
            return {"ok": True, "lines": []}
        except Exception as e:
            return {"ok": False, "msg": str(e)}


# ═══════════════════════════════════════════════════════════════
#  MAIN — arranca PyWebView
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    api = ContaSATAPI()

    window = webview.create_window(
        title      = "ContaSAT — Gestión de CFDIs",
        url        = str(GUI_FILE),
        js_api     = api,
        width      = 1280,
        height     = 800,
        min_size   = (1024, 680),
        resizable  = True,
        text_select= False,
    )
    api._window = window

    webview.start(debug=False)
