"""
ContaSAT - app.py v3.0
Backend Flask. Sirve la GUI en localhost y expone /api/* endpoints.
Sin pywebview, sin pythonnet, sin compilar nada.
Ejecutar: python app.py
"""

import base64
import datetime
import json
import logging
import os
import sys
import threading
import webbrowser
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Verificar dependencias ────────────────────────────────────
def _verificar_deps():
    faltantes = []
    for m in ["flask", "satcfdi", "openpyxl"]:
        try:
            __import__(m)
        except ImportError:
            faltantes.append(m)
    if faltantes:
        print(f"[ERROR] Faltan dependencias: {faltantes}")
        print("Ejecuta iniciar_contasat.bat para instalarlas.")
        input("Presiona Enter para cerrar...")
        sys.exit(1)

_verificar_deps()

from flask import Flask, jsonify, request, send_file, send_from_directory
from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, TipoDescargaMasivaTerceros
import openpyxl
from openpyxl.styles import Font, PatternFill

# ── Rutas ─────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
GUI_FILE  = BASE_DIR / "contasat_gui.html"
DATA_DIR  = BASE_DIR.parent / "contabilidad_sat"
HIST_FILE = DATA_DIR / "historial.json"
LOG_FILE  = DATA_DIR / "descarga_sat.log"
CFG_FILE  = BASE_DIR.parent / "config.json"
PORT      = 5120

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

# ── Estado de sesion ─────────────────────────────────────────
_signer      = None
_sat         = None
_log_lines   = []
_progreso    = 0
_descargando = False

# ── Config ────────────────────────────────────────────────────
CFG_DEFAULT = {
    "rfc": "", "fiel_cer": "", "fiel_key": "",
    "fiel_cer_nombre": "", "fiel_key_nombre": "",
    "notif_email": "", "notif_cc": "",
    "dia_auto": 1, "hora_auto": "08:00",
    "nombre": "", "regimen": "",
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
            "tipo": tipo, "uuid": a(tfd, "UUID"),
            "fecha": fecha[:10], "serie": root.get("Serie", ""),
            "folio": root.get("Folio", ""),
            "rfc_emisor": a(emisor, "Rfc"), "nombre_emisor": a(emisor, "Nombre"),
            "rfc_receptor": a(receptor, "Rfc"), "nombre_receptor": a(receptor, "Nombre"),
            "uso_cfdi": a(receptor, "UsoCFDI"), "descripcion": a(concepto, "Descripcion"),
            "subtotal": root.get("SubTotal", ""), "total": total,
            "moneda": root.get("Moneda", "MXN"),
            "tipo_comp": root.get("TipoDeComprobante", ""),
            "metodo_pago": root.get("MetodoPago", ""),
            "forma_pago": root.get("FormaPago", ""),
            "archivo": ruta.name,
        }
    except Exception as e:
        return {"tipo": tipo, "archivo": ruta.name, "error": str(e), "total": 0}

def _emit(msg: str, level: str = "info"):
    log.info(msg)
    _log_lines.append({"msg": msg, "level": level,
                        "ts": datetime.datetime.now().strftime("%H:%M:%S")})
    if len(_log_lines) > 500:
        _log_lines.pop(0)

# ══════════════════════════════════════════════════════════════
#  FLASK
# ══════════════════════════════════════════════════════════════
app = Flask(__name__)

@app.route("/")
def index():
    return send_file(str(GUI_FILE))

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(BASE_DIR), filename)

# ── Config ────────────────────────────────────────────────────
@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(_load_cfg())

@app.route("/api/config", methods=["POST"])
def save_config():
    try:
        cfg = _load_cfg()
        cfg.update(request.get_json() or {})
        _save_cfg(cfg)
        return jsonify({"ok": True, "msg": "Configuracion guardada."})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

# ── e.firma ───────────────────────────────────────────────────
@app.route("/api/fiel/status", methods=["GET"])
def fiel_status():
    cfg = _load_cfg()
    return jsonify({
        "cargada":     _signer is not None,
        "cer_nombre":  cfg.get("fiel_cer_nombre", ""),
        "key_nombre":  cfg.get("fiel_key_nombre", ""),
        "cer_ruta":    cfg.get("fiel_cer", ""),
        "key_ruta":    cfg.get("fiel_key", ""),
        "tiene_rutas": bool(cfg.get("fiel_cer") and cfg.get("fiel_key")),
    })

@app.route("/api/fiel/cargar", methods=["POST"])
def cargar_fiel():
    global _signer, _sat
    try:
        d = request.get_json() or {}
        cer_b64  = d.get("cer_b64", "")
        key_b64  = d.get("key_b64", "")
        password = d.get("password", "")
        cer_nombre = d.get("cer_nombre", "")
        key_nombre = d.get("key_nombre", "")
        cer_ruta = d.get("cer_ruta", "")
        key_ruta = d.get("key_ruta", "")

        if cer_ruta and key_ruta and not cer_b64:
            cp = Path(cer_ruta); kp = Path(key_ruta)
            if not cp.exists():
                return jsonify({"ok": False, "msg": f"No se encontro: {cp.name}"})
            if not kp.exists():
                return jsonify({"ok": False, "msg": f"No se encontro: {kp.name}"})
            cer_bytes  = cp.read_bytes()
            key_bytes  = kp.read_bytes()
            cer_nombre = cer_nombre or cp.name
            key_nombre = key_nombre or kp.name
        else:
            if not cer_b64 or not key_b64:
                return jsonify({"ok": False, "msg": "Carga los archivos .cer y .key."})
            cer_bytes = base64.b64decode(cer_b64)
            key_bytes = base64.b64decode(key_b64)

        pwd = password.encode("utf-8") if isinstance(password, str) else password
        _signer = Signer.load(certificate=cer_bytes, key=key_bytes, password=pwd)
        _sat    = SAT(signer=_signer)
        rfc     = _signer.rfc
        log.info(f"Signer cargado. RFC: {rfc}")

        cfg = _load_cfg()
        if cer_ruta: cfg["fiel_cer"] = cer_ruta
        if key_ruta: cfg["fiel_key"] = key_ruta
        cfg.update({"fiel_cer_nombre": cer_nombre,
                    "fiel_key_nombre": key_nombre, "rfc": rfc})
        _save_cfg(cfg)

        return jsonify({"ok": True, "msg": f"e.firma valida. RFC: {rfc}",
                        "rfc": rfc, "cer_nombre": cer_nombre, "key_nombre": key_nombre})
    except Exception as e:
        _signer = None; _sat = None
        msg = str(e)
        if "password" in msg.lower() or "decrypt" in msg.lower():
            msg = "Contrasena incorrecta."
        elif "certificate" in msg.lower():
            msg = "Archivo .cer invalido."
        elif "key" in msg.lower():
            msg = "Archivo .key invalido."
        return jsonify({"ok": False, "msg": f"Error e.firma: {msg}"})

@app.route("/api/fiel/cargar-guardada", methods=["POST"])
def cargar_fiel_guardada():
    cfg      = _load_cfg()
    password = (request.get_json() or {}).get("password", "")
    with app.test_request_context(
        "/api/fiel/cargar", method="POST",
        json={"cer_ruta": cfg.get("fiel_cer",""),
              "key_ruta": cfg.get("fiel_key",""),
              "password": password},
        content_type="application/json"
    ):
        return cargar_fiel()

# ── Rango ─────────────────────────────────────────────────────
@app.route("/api/rango/automatico", methods=["GET"])
def rango_automatico():
    h   = _load_hist()
    hoy = datetime.date.today()
    if h["primera_ejecucion"] or not h["ultima_fecha"]:
        ini  = datetime.date(hoy.year, 1, 1)
        modo = "primera"
    else:
        ultima = datetime.date.fromisoformat(h["ultima_fecha"])
        ini    = ultima - datetime.timedelta(days=1)
        modo   = "incremental"
    return jsonify({"inicio": str(ini), "fin": str(hoy),
                    "modo": modo, "primera_ejecucion": h["primera_ejecucion"]})

# ── Historial ─────────────────────────────────────────────────
@app.route("/api/historial", methods=["GET"])
def get_historial():
    return jsonify(_load_hist())

@app.route("/api/historial/limpiar", methods=["POST"])
def limpiar_historial():
    try:
        _save_hist({"primera_ejecucion": True, "ultima_fecha": None,
                    "uuids": [], "ejecuciones": []})
        return jsonify({"ok": True, "msg": "Historial limpiado."})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

# ── Descarga ──────────────────────────────────────────────────
@app.route("/api/descarga/iniciar", methods=["POST"])
def iniciar_descarga():
    global _descargando
    if not _sat:
        return jsonify({"ok": False, "msg": "Carga y valida tu e.firma primero."})
    if _descargando:
        return jsonify({"ok": False, "msg": "Ya hay una descarga en proceso."})
    d = request.get_json() or {}
    threading.Thread(
        target=_descarga_worker,
        args=(d.get("inicio"), d.get("fin"), d.get("tipo_cfdi", "ambas")),
        daemon=True,
    ).start()
    return jsonify({"ok": True, "msg": "Descarga iniciada en segundo plano."})

def _descarga_worker(inicio: str, fin: str, tipo_cfdi: str):
    global _progreso, _descargando
    _descargando = True
    _progreso    = 0
    _log_lines.clear()

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

            _emit(f"Solicitando CFDIs {tipo.upper()} {fecha_ini} -> {fecha_fin}...", "info")
            kwargs = dict(fecha_inicial=fecha_ini, fecha_final=fecha_fin,
                          tipo_solicitud=TipoDescargaMasivaTerceros.CFDI)
            if tipo == "recibidas": kwargs["rfc_receptor"] = _signer.rfc
            else:                   kwargs["rfc_emisor"]   = _signer.rfc

            n = 0
            for paquete_id, data in _sat.recover_comprobante_iwait(**kwargs):
                n += 1
                _emit(f"Paquete {paquete_id} descargado.", "info")
                ruta_zip = carp_zip / f"{paquete_id}.zip"
                ruta_zip.write_bytes(data)
                with zipfile.ZipFile(ruta_zip) as z:
                    for nombre in [x for x in z.namelist() if x.lower().endswith(".xml")]:
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
                _progreso = int((paso + min(n * 0.1, 0.9)) / len(tipos) * 90)

            if n == 0:
                _emit(f"Sin CFDIs {tipo.upper()} en el periodo.", "warn")
            else:
                _emit(f"{tipo.upper()}: {n} paquetes OK.", "ok")

        if todos:
            _emit("Generando reporte Excel...", "info")
            _generar_excel(todos, base / "reportes", fecha_ini, fecha_fin)

        hist["primera_ejecucion"]  = False
        hist["ultima_fecha"]       = str(fecha_fin)
        hist["uuids"]              = list(uuids)
        hist["ejecuciones"].append({
            "fecha": datetime.datetime.now().isoformat(),
            "inicio": str(fecha_ini), "fin": str(fecha_fin),
            "total": len(todos), "nuevos": nuevos, "overwrite": overwr,
        })
        _save_hist(hist)
        _progreso = 100
        _emit(f"COMPLETADO: {len(todos)} CFDIs | {nuevos} nuevos | {overwr} overwrite", "ok")
    except Exception as e:
        _emit(f"Error: {e}", "error")
    finally:
        _descargando = False

@app.route("/api/descarga/estado", methods=["GET"])
def estado_descarga():
    desde = int(request.args.get("desde", 0))
    return jsonify({
        "progreso":    _progreso,
        "descargando": _descargando,
        "log":         _log_lines[desde:],
        "total_log":   len(_log_lines),
    })

# ── Facturas ─────────────────────────────────────────────────
@app.route("/api/facturas", methods=["GET"])
def get_facturas():
    try:
        tipo = request.args.get("tipo", "todas")
        anio = request.args.get("anio")
        mes  = request.args.get("mes")
        resultados = []
        for xml in DATA_DIR.rglob("*.xml"):
            partes = xml.parts
            if "emitidas"   in partes: t = "Emitida"
            elif "recibidas" in partes: t = "Recibida"
            else: t = "Desconocida"
            if tipo == "emitidas"  and t != "Emitida":  continue
            if tipo == "recibidas" and t != "Recibida": continue
            cfdi = _parsear(xml, t)
            if anio and cfdi.get("fecha","")[:4]  != str(anio):         continue
            if mes  and cfdi.get("fecha","")[5:7] != f"{int(mes):02d}": continue
            resultados.append(cfdi)
        return jsonify({"ok": True, "data": resultados, "total": len(resultados)})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e), "data": []})

@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    try:
        xmls      = list(DATA_DIR.rglob("*.xml"))
        emitidas  = [_parsear(x,"Emitida")  for x in xmls if "emitidas"  in x.parts]
        recibidas = [_parsear(x,"Recibida") for x in xmls if "recibidas" in x.parts]
        emitidas  = [f for f in emitidas  if "error" not in f]
        recibidas = [f for f in recibidas if "error" not in f]
        hist      = _load_hist()
        return jsonify({
            "total_emitidas":  len(emitidas),
            "total_recibidas": len(recibidas),
            "monto_emitido":   round(sum(f.get("total",0) for f in emitidas),  2),
            "monto_recibido":  round(sum(f.get("total",0) for f in recibidas), 2),
            "balance":         round(sum(f.get("total",0) for f in emitidas) -
                                     sum(f.get("total",0) for f in recibidas), 2),
            "ultima_descarga": hist.get("ultima_fecha","Sin descargas"),
            "total_uuids":     len(hist.get("uuids",[])),
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/reporte/excel", methods=["POST"])
def generar_reporte():
    try:
        xmls  = list(DATA_DIR.rglob("*.xml"))
        datos = ([_parsear(x,"Emitida")  for x in xmls if "emitidas"  in x.parts] +
                 [_parsear(x,"Recibida") for x in xmls if "recibidas" in x.parts])
        datos = [f for f in datos if "error" not in f]
        hoy   = datetime.date.today()
        ruta  = _generar_excel(datos, DATA_DIR/"reportes",
                               datetime.date(hoy.year,1,1), hoy)
        return jsonify({"ok": True, "msg": f"Reporte guardado: {ruta}", "ruta": ruta})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

def _generar_excel(datos, carpeta, fecha_ini, fecha_fin):
    carpeta.mkdir(parents=True, exist_ok=True)
    wb  = openpyxl.Workbook()
    fh  = PatternFill("solid", fgColor="1F3864")
    fnt = Font(color="FFFFFF", bold=True)
    emi = [d for d in datos if d.get("tipo")=="Emitida"]
    rec = [d for d in datos if d.get("tipo")=="Recibida"]
    suma = lambda l: round(sum(d.get("total",0) for d in l), 2)
    ws = wb.active; ws.title = "Resumen"
    for r,(k,v) in enumerate([
        ("Periodo",f"{fecha_ini} -> {fecha_fin}"),
        ("Facturas emitidas",len(emi)),("Total emitido MXN",suma(emi)),
        ("Facturas recibidas",len(rec)),("Total recibido MXN",suma(rec)),
        ("Balance",suma(emi)-suma(rec))
    ],1):
        ws.cell(r,1,k).font=Font(bold=True); ws.cell(r,2,v)
    COLS=["tipo","uuid","fecha","rfc_emisor","nombre_emisor","rfc_receptor",
          "nombre_receptor","descripcion","subtotal","total","moneda","tipo_comp","archivo"]
    for nombre,filas in [("Emitidas",emi),("Recibidas",rec)]:
        wsd=wb.create_sheet(nombre)
        for c,col in enumerate(COLS,1):
            cell=wsd.cell(1,c,col.replace("_"," ").title())
            cell.fill=fh; cell.font=fnt
        for r,d in enumerate(filas,2):
            for c,col in enumerate(COLS,1): wsd.cell(r,c,d.get(col,""))
        wsd.auto_filter.ref=wsd.dimensions
    ruta=carpeta/f"CFDIs_{fecha_ini}_{fecha_fin}.xlsx"
    wb.save(ruta); _emit(f"Excel: {ruta}","ok")
    return str(ruta)

@app.route("/api/sistema/abrir-carpeta", methods=["POST"])
def abrir_carpeta():
    try:
        os.startfile(str(DATA_DIR))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

@app.route("/api/sistema/log", methods=["GET"])
def get_log():
    try:
        lines = LOG_FILE.read_text("utf-8").splitlines()[-100:] if LOG_FILE.exists() else []
        return jsonify({"ok": True, "lines": lines})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

# ── Arranque ──────────────────────────────────────────────────
if __name__ == "__main__":
    if not GUI_FILE.exists():
        print(f"[ERROR] GUI no encontrada: {GUI_FILE}")
        input("Presiona Enter para cerrar...")
        sys.exit(1)

    url = f"http://localhost:{PORT}"
    print(f"\n  ContaSAT v3.0 iniciando en {url}")
    print(f"  Abriendo en el navegador...")
    print(f"  Para cerrar la aplicacion cierra esta ventana.\n")

    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
