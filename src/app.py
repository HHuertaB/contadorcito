"""
ContaSAT — app.py  v2.0
Backend principal usando satcfdi (reemplaza cfdiclient).
Ejecutar: python app.py
"""

import base64
import datetime
import json
import logging
import os
import sys
import threading
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Verificar dependencias criticas ───────────────────────────
def _verificar_deps():
    faltantes = []
    for modulo in ["webview", "satcfdi", "openpyxl"]:
        try:
            __import__(modulo)
        except ImportError:
            faltantes.append(modulo)
    if faltantes:
        print(f"[ERROR] Faltan dependencias: {faltantes}")
        print("Ejecuta iniciar_contasat.bat para instalarlas.")
        input("Presiona Enter para cerrar...")
        sys.exit(1)

_verificar_deps()

import webview
from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, TipoDescargaMasivaTerceros
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# ── Rutas base ─────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
GUI_FILE  = BASE_DIR / "contasat_gui.html"
DATA_DIR  = BASE_DIR.parent / "contabilidad_sat"
HIST_FILE = DATA_DIR / "historial.json"
LOG_FILE  = DATA_DIR / "descarga_sat.log"
CFG_FILE  = BASE_DIR.parent / "config.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────
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

# ── Config ─────────────────────────────────────────────────────
CFG_DEFAULT = {
    "rfc": "",
    "fiel_cer": "",
    "fiel_key": "",
    "fiel_cer_nombre": "",
    "fiel_key_nombre": "",
    "notif_email": "",
    "notif_cc": "",
    "dia_auto": 1,
    "hora_auto": "08:00",
    "nombre": "",
    "regimen": "",
}

def _load_cfg():
    if CFG_FILE.exists():
        try:
            return {**CFG_DEFAULT, **json.loads(CFG_FILE.read_text("utf-8"))}
        except Exception:
            pass
    return dict(CFG_DEFAULT)

def _save_cfg(cfg):
    CFG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")

def _load_hist():
    if HIST_FILE.exists():
        try:
            return json.loads(HIST_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {"primera_ejecucion": True, "ultima_fecha": None,
            "uuids": [], "ejecuciones": []}

def _save_hist(h):
    HIST_FILE.write_text(
        json.dumps(h, indent=2, ensure_ascii=False, default=str), "utf-8"
    )

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
            "tipo":            tipo,
            "uuid":            a(tfd,      "UUID"),
            "fecha":           fecha[:10],
            "serie":           root.get("Serie", ""),
            "folio":           root.get("Folio", ""),
            "rfc_emisor":      a(emisor,   "Rfc"),
            "nombre_emisor":   a(emisor,   "Nombre"),
            "rfc_receptor":    a(receptor, "Rfc"),
            "nombre_receptor": a(receptor, "Nombre"),
            "uso_cfdi":        a(receptor, "UsoCFDI"),
            "descripcion":     a(concepto, "Descripcion"),
            "subtotal":        root.get("SubTotal", ""),
            "total":           total,
            "moneda":          root.get("Moneda", "MXN"),
            "tipo_comp":       root.get("TipoDeComprobante", ""),
            "metodo_pago":     root.get("MetodoPago", ""),
            "forma_pago":      root.get("FormaPago", ""),
            "archivo":         ruta.name,
        }
    except Exception as e:
        return {"tipo": tipo, "archivo": ruta.name, "error": str(e), "total": 0}


# ══════════════════════════════════════════════════════════════
#  API expuesta a JavaScript via PyWebView
# ══════════════════════════════════════════════════════════════
class ContaSATAPI:

    def __init__(self):
        self._window = None
        self._signer = None
        self._sat    = None

    # ── Comunicacion con la GUI ───────────────────────────────
    def _emit(self, msg: str, level: str = "info"):
        log.info(msg)
        if self._window:
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

    # ── Configuracion ─────────────────────────────────────────
    def get_config(self) -> dict:
        return _load_cfg()

    def save_config(self, cfg: dict) -> dict:
        try:
            current = _load_cfg()
            current.update(cfg)
            _save_cfg(current)
            return {"ok": True, "msg": "Configuracion guardada."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ── e.firma ───────────────────────────────────────────────
    def cargar_fiel(self, cer_b64: str = "", key_b64: str = "",
                    password: str = "", cer_nombre: str = "",
                    key_nombre: str = "", cer_ruta: str = "",
                    key_ruta: str = "") -> dict:
        try:
            if cer_ruta and key_ruta and not cer_b64:
                cer_path = Path(cer_ruta)
                key_path = Path(key_ruta)
                if not cer_path.exists():
                    return {"ok": False, "msg": f"No se encontro: {cer_path.name}"}
                if not key_path.exists():
                    return {"ok": False, "msg": f"No se encontro: {key_path.name}"}
                cer_bytes  = cer_path.read_bytes()
                key_bytes  = key_path.read_bytes()
                cer_nombre = cer_nombre or cer_path.name
                key_nombre = key_nombre or key_path.name
            else:
                if not cer_b64 or not key_b64:
                    return {"ok": False, "msg": "Carga los archivos .cer y .key."}
                cer_bytes = base64.b64decode(cer_b64)
                key_bytes = base64.b64decode(key_b64)

            pwd = password.encode("utf-8") if isinstance(password, str) else password
            self._signer = Signer.load(
                certificate=cer_bytes,
                key=key_bytes,
                password=pwd,
            )
            self._sat = SAT(signer=self._signer)
            rfc = self._signer.rfc
            log.info(f"Signer cargado. RFC: {rfc}")

            cfg = _load_cfg()
            if cer_ruta: cfg["fiel_cer"] = cer_ruta
            if key_ruta: cfg["fiel_key"] = key_ruta
            cfg["fiel_cer_nombre"] = cer_nombre
            cfg["fiel_key_nombre"] = key_nombre
            cfg["rfc"] = rfc
            _save_cfg(cfg)

            return {"ok": True, "msg": f"e.firma valida. RFC: {rfc}",
                    "rfc": rfc, "cer_nombre": cer_nombre, "key_nombre": key_nombre}

        except Exception as e:
            self._signer = None
            self._sat    = None
            msg = str(e)
            if "password" in msg.lower() or "decrypt" in msg.lower():
                msg = "Contrasena incorrecta."
            elif "certificate" in msg.lower():
                msg = "Archivo .cer invalido."
            elif "key" in msg.lower():
                msg = "Archivo .key invalido."
            return {"ok": False, "msg": f"Error al cargar e.firma: {msg}"}

    def cargar_fiel_desde_rutas_guardadas(self, password: str) -> dict:
        cfg = _load_cfg()
        cer = cfg.get("fiel_cer", "")
        key = cfg.get("fiel_key", "")
        if not cer or not key:
            return {"ok": False, "msg": "No hay rutas guardadas. Carga manualmente."}
        return self.cargar_fiel(password=password, cer_ruta=cer, key_ruta=key)

    def get_fiel_status(self) -> dict:
        cfg = _load_cfg()
        return {
            "cargada":     self._signer is not None,
            "cer_nombre":  cfg.get("fiel_cer_nombre", ""),
            "key_nombre":  cfg.get("fiel_key_nombre", ""),
            "cer_ruta":    cfg.get("fiel_cer", ""),
            "key_ruta":    cfg.get("fiel_key", ""),
            "tiene_rutas": bool(cfg.get("fiel_cer") and cfg.get("fiel_key")),
        }

    # ── Rango inteligente ─────────────────────────────────────
    def get_rango_automatico(self) -> dict:
        h   = _load_hist()
        hoy = datetime.date.today()
        if h["primera_ejecucion"] or not h["ultima_fecha"]:
            ini  = datetime.date(hoy.year, 1, 1)
            modo = "primera"
        else:
            ultima = datetime.date.fromisoformat(h["ultima_fecha"])
            ini    = ultima - datetime.timedelta(days=1)
            modo   = "incremental"
        return {"inicio": str(ini), "fin": str(hoy),
                "modo": modo, "primera_ejecucion": h["primera_ejecucion"]}

    def get_historial(self) -> dict:
        return _load_hist()

    def limpiar_historial(self) -> dict:
        try:
            _save_hist({"primera_ejecucion": True, "ultima_fecha": None,
                        "uuids": [], "ejecuciones": []})
            return {"ok": True, "msg": "Historial limpiado."}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ── Descarga SAT ──────────────────────────────────────────
    def iniciar_descarga(self, inicio: str, fin: str,
                         tipo_cfdi: str = "ambas") -> dict:
        if not self._sat:
            return {"ok": False, "msg": "Carga y valida tu e.firma primero."}
        t = threading.Thread(
            target=self._descarga_worker,
            args=(inicio, fin, tipo_cfdi),
            daemon=True,
        )
        t.start()
        return {"ok": True, "msg": "Descarga iniciada en segundo plano."}

    def _descarga_worker(self, inicio: str, fin: str, tipo_cfdi: str):
        fecha_ini = datetime.date.fromisoformat(inicio)
        fecha_fin = datetime.date.fromisoformat(fin)
        hist      = _load_hist()
        uuids     = set(hist.get("uuids", []))
        todos     = []
        nuevos = overwr = 0

        base  = DATA_DIR / str(fecha_ini.year) / f"{fecha_ini.month:02d}"
        tipos = []
        if tipo_cfdi in ("ambas", "recibidas"): tipos.append("recibidas")
        if tipo_cfdi in ("ambas", "emitidas"):  tipos.append("emitidas")

        try:
            for paso, tipo in enumerate(tipos):
                carp_zip = base / tipo / "zips"
                carp_xml = base / tipo / "xml"
                carp_zip.mkdir(parents=True, exist_ok=True)
                carp_xml.mkdir(parents=True, exist_ok=True)

                self._emit(
                    f"Solicitando CFDIs {tipo.upper()} "
                    f"{fecha_ini} -> {fecha_fin}...", "info"
                )

                kwargs = dict(
                    fecha_inicial  = fecha_ini,
                    fecha_final    = fecha_fin,
                    tipo_solicitud = TipoDescargaMasivaTerceros.CFDI,
                )
                if tipo == "recibidas":
                    kwargs["rfc_receptor"] = self._signer.rfc
                else:
                    kwargs["rfc_emisor"] = self._signer.rfc

                n = 0
                for paquete_id, data in self._sat.recover_comprobante_iwait(**kwargs):
                    n += 1
                    self._emit(f"Paquete {paquete_id} descargado.", "info")
                    (carp_zip / f"{paquete_id}.zip").write_bytes(data)

                    with zipfile.ZipFile(carp_zip / f"{paquete_id}.zip") as z:
                        for nombre in [x for x in z.namelist()
                                       if x.lower().endswith(".xml")]:
                            contenido = z.read(nombre)
                            ruta_xml  = carp_xml / nombre
                            ruta_xml.write_bytes(contenido)
                            label = "Emitida" if tipo == "emitidas" else "Recibida"
                            cfdi  = _parsear(ruta_xml, label)
                            uuid  = cfdi.get("uuid", "")
                            if uuid:
                                if uuid in uuids: overwr += 1
                                else: uuids.add(uuid); nuevos += 1
                            todos.append(cfdi)

                    self._emit_progress(int((paso + n * 0.1) / len(tipos) * 90))

                if n == 0:
                    self._emit(f"Sin CFDIs {tipo.upper()} en el periodo.", "warn")
                else:
                    self._emit(f"{tipo.upper()}: {n} paquetes procesados.", "ok")

            if todos:
                self._emit("Generando reporte Excel...", "info")
                self._generar_excel(todos, base / "reportes", fecha_ini, fecha_fin)

            hist["primera_ejecucion"]  = False
            hist["ultima_fecha"]       = str(fecha_fin)
            hist["uuids"]              = list(uuids)
            hist["ejecuciones"].append({
                "fecha":     datetime.datetime.now().isoformat(),
                "inicio":    str(fecha_ini),
                "fin":       str(fecha_fin),
                "total":     len(todos),
                "nuevos":    nuevos,
                "overwrite": overwr,
            })
            _save_hist(hist)

            self._emit_progress(100)
            self._emit(
                f"COMPLETADO: {len(todos)} CFDIs | "
                f"{nuevos} nuevos | {overwr} overwrite", "ok"
            )
            self._emit_event("descarga_completada",
                             {"total": len(todos), "nuevos": nuevos, "overwrite": overwr})

        except Exception as e:
            self._emit(f"Error: {e}", "error")
            self._emit_event("descarga_error", {"msg": str(e)})

    # ── Excel ─────────────────────────────────────────────────
    def _generar_excel(self, datos, carpeta, fecha_ini, fecha_fin):
        carpeta.mkdir(parents=True, exist_ok=True)
        wb  = openpyxl.Workbook()
        fh  = PatternFill("solid", fgColor="1F3864")
        fnt = Font(color="FFFFFF", bold=True)
        emitidas  = [d for d in datos if d.get("tipo") == "Emitida"  and "error" not in d]
        recibidas = [d for d in datos if d.get("tipo") == "Recibida" and "error" not in d]
        suma = lambda lst: round(sum(d.get("total", 0) for d in lst), 2)

        ws = wb.active; ws.title = "Resumen"
        for r, (k, v) in enumerate([
            ("Periodo",            f"{fecha_ini} -> {fecha_fin}"),
            ("Facturas emitidas",  len(emitidas)),
            ("Total emitido MXN",  suma(emitidas)),
            ("Facturas recibidas", len(recibidas)),
            ("Total recibido MXN", suma(recibidas)),
            ("Balance",            suma(emitidas) - suma(recibidas)),
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
                cell.fill = fh; cell.font = fnt
            for r, d in enumerate(filas, 2):
                for c, col in enumerate(COLS, 1):
                    wsd.cell(r, c, d.get(col, ""))
            wsd.auto_filter.ref = wsd.dimensions

        ruta = carpeta / f"CFDIs_{fecha_ini}_{fecha_fin}.xlsx"
        wb.save(ruta)
        self._emit(f"Excel: {ruta}", "ok")
        return str(ruta)

    def generar_reporte(self, tipo: str = "excel") -> dict:
        try:
            result = self.get_facturas()
            if not result["ok"]: return result
            hoy  = datetime.date.today()
            ruta = self._generar_excel(
                result["data"], DATA_DIR / "reportes",
                datetime.date(hoy.year, 1, 1), hoy,
            )
            return {"ok": True, "msg": f"Reporte: {ruta}", "ruta": ruta}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    # ── Facturas ─────────────────────────────────────────────
    def get_facturas(self, anio: int = None, mes: int = None,
                     tipo: str = "todas") -> dict:
        try:
            resultados = []
            for xml in DATA_DIR.rglob("*.xml"):
                partes = xml.parts
                if "emitidas"  in partes: t = "Emitida"
                elif "recibidas" in partes: t = "Recibida"
                else: t = "Desconocida"
                if tipo == "emitidas"  and t != "Emitida":  continue
                if tipo == "recibidas" and t != "Recibida": continue
                cfdi = _parsear(xml, t)
                if anio and cfdi.get("fecha", "")[:4]  != str(anio):      continue
                if mes  and cfdi.get("fecha", "")[5:7] != f"{mes:02d}":   continue
                resultados.append(cfdi)
            return {"ok": True, "data": resultados, "total": len(resultados)}
        except Exception as e:
            return {"ok": False, "msg": str(e), "data": []}

    def get_dashboard_stats(self) -> dict:
        try:
            result    = self.get_facturas()
            if not result["ok"]: return {}
            facturas  = result["data"]
            emitidas  = [f for f in facturas if f.get("tipo") == "Emitida"  and "error" not in f]
            recibidas = [f for f in facturas if f.get("tipo") == "Recibida" and "error" not in f]
            hist      = _load_hist()
            return {
                "total_emitidas":  len(emitidas),
                "total_recibidas": len(recibidas),
                "monto_emitido":   round(sum(f.get("total", 0) for f in emitidas),  2),
                "monto_recibido":  round(sum(f.get("total", 0) for f in recibidas), 2),
                "balance":         round(sum(f.get("total", 0) for f in emitidas) -
                                         sum(f.get("total", 0) for f in recibidas), 2),
                "ultima_descarga": hist.get("ultima_fecha", "Sin descargas"),
                "total_uuids":     len(hist.get("uuids", [])),
            }
        except Exception as e:
            return {"error": str(e)}

    def abrir_carpeta(self) -> dict:
        try:
            os.startfile(str(DATA_DIR))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def get_log_reciente(self) -> dict:
        try:
            lines = LOG_FILE.read_text("utf-8").splitlines() if LOG_FILE.exists() else []
            return {"ok": True, "lines": lines[-100:]}
        except Exception as e:
            return {"ok": False, "msg": str(e)}


# ── Arranque ──────────────────────────────────────────────────
if __name__ == "__main__":
    if not GUI_FILE.exists():
        print(f"[ERROR] GUI no encontrada: {GUI_FILE}")
        input("Presiona Enter para cerrar...")
        sys.exit(1)

    api    = ContaSATAPI()
    window = webview.create_window(
        title     = "ContaSAT - Gestion de CFDIs",
        url       = str(GUI_FILE),
        js_api    = api,
        width     = 1280,
        height    = 800,
        min_size  = (1024, 680),
        resizable = True,
    )
    api._window = window
    webview.start(debug=False)
