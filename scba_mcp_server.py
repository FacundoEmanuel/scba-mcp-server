"""
SCBA MCP Server — Suprema Corte de Buenos Aires
Expone los tres portales de sentencias como herramientas MCP:
  · Primera Instancia  → sentencias.scba.gov.ar
  · Cámaras            → sentencias-camara.scba.gov.ar
  · Corte Suprema      → sentencias-corte.scba.gov.ar

Instalación:
    pip install mcp selenium

Uso con Claude Desktop  →  ver claude_desktop_config.json
Uso con MCP Inspector   →  npx @modelcontextprotocol/inspector python scba_mcp_server.py
"""

from __future__ import annotations

import os
import re
import time
import random
from typing import Optional
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# ── Selenium (importación diferida para no romper el import del servidor)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False


# ─────────────────────────────────────────────
#  Configuración de portales
# ─────────────────────────────────────────────

PORTALES = {
    "primera_instancia": {
        "nombre":      "Primera Instancia",
        "url":         "https://sentencias.scba.gov.ar/",
        "descripcion": "Juzgados civiles, laborales y contencioso-administrativos de primera instancia",
    },
    "camara": {
        "nombre":      "Cámaras de Apelación",
        "url":         "https://sentencias-camara.scba.gov.ar/",
        "descripcion": "Cámaras de Apelación departamentales de la Provincia de Buenos Aires",
    },
    "corte": {
        "nombre":      "Corte Suprema",
        "url":         "https://sentencias-corte.scba.gov.ar/",
        "descripcion": "Suprema Corte de Justicia de la Provincia de Buenos Aires",
    },
}

PORTAL_DEFAULT = "primera_instancia"


# ─────────────────────────────────────────────
#  Instancia del servidor MCP
# ─────────────────────────────────────────────

mcp = FastMCP(
    "SCBA Sentencias",
    instructions=(
        "Servidor de sentencias judiciales de la Suprema Corte de Buenos Aires. "
        "Cubre tres portales: primera_instancia, camara y corte. "
        "Siempre llamá primero a `listar_organismos` con el portal correcto antes de buscar documentos. "
        "Usá `listar_portales` para ver los portales disponibles."
    ),
)


# ─────────────────────────────────────────────
#  Estado global — un driver por portal
# ─────────────────────────────────────────────

_drivers: dict[str, webdriver.Chrome] = {}

TIEMPO_ESPERA_MIN = 2
TIEMPO_ESPERA_MAX = 4


def _pausa(min_t: float = TIEMPO_ESPERA_MIN, max_t: float = TIEMPO_ESPERA_MAX) -> None:
    time.sleep(random.uniform(min_t, max_t))


def _get_driver(portal: str) -> tuple[webdriver.Chrome, WebDriverWait]:
    """Devuelve el driver singleton para el portal dado, iniciándolo si es necesario."""
    if not SELENIUM_OK:
        raise RuntimeError("Selenium no está instalado. Ejecutá: pip install selenium")

    if portal not in PORTALES:
        raise ValueError(f"Portal inválido: '{portal}'. Usá: {list(PORTALES.keys())}")

    if portal not in _drivers:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        try:
            s = Service(executable_path="chromedriver.exe")
            driver = webdriver.Chrome(service=s, options=options)
        except Exception:
            driver = webdriver.Chrome(options=options)

        driver.get(PORTALES[portal]["url"])
        time.sleep(5)
        _drivers[portal] = driver

    driver = _drivers[portal]
    wait = WebDriverWait(driver, 30)
    return driver, wait


def _cerrar_driver(portal: str) -> None:
    if portal in _drivers:
        try:
            _drivers[portal].quit()
        except Exception:
            pass
        del _drivers[portal]


def _cerrar_todos() -> None:
    for portal in list(_drivers.keys()):
        _cerrar_driver(portal)


# ─────────────────────────────────────────────
#  Helpers de scraping
# ─────────────────────────────────────────────

def _validar_fecha(fecha: str) -> bool:
    try:
        datetime.strptime(fecha, "%d/%m/%Y")
        return True
    except ValueError:
        return False


def _limpiar_nombre(texto: str) -> str:
    texto = re.sub(r"^causa:?", "", texto, flags=re.IGNORECASE)
    return re.sub(r'[<>:"/\\|?*]', "", texto).strip()[:150]


def _extraer_texto_modal(driver: webdriver.Chrome) -> str:
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card-body")))
    cards = driver.find_elements(By.CLASS_NAME, "card-body")
    return "\n".join(c.text for c in cards if c.text.strip())


def _cerrar_modal(driver: webdriver.Chrome) -> None:
    try:
        wait = WebDriverWait(driver, 8)
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Cerrar')]")
        )).click()
    except Exception:
        try:
            ActionChains(driver).move_by_offset(50, 100).click().perform()
            ActionChains(driver).move_by_offset(-50, -100).perform()
        except Exception:
            pass


def _escribir_lento(element, texto: str, delay: float = 0.15) -> None:
    element.clear()
    for ch in texto:
        element.send_keys(ch)
        time.sleep(delay)


def _seleccionar_tipo_registro(wait: WebDriverWait, tipo_registro: str) -> None:
    """Selecciona el tipo de registro (sentencias/resoluciones) en el dropdown."""
    wait.until(EC.element_to_be_clickable((By.ID, "select2-Registros-container"))).click()
    _pausa(1, 2)

    opciones = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//li[contains(@class,'select2-results__option')]")
        )
    )
    opciones_visibles = [o for o in opciones if o.text.strip()]
    idx = 1 if tipo_registro == "resoluciones" else 2
    if idx < len(opciones_visibles):
        opciones_visibles[idx].click()
    _pausa()


# ─────────────────────────────────────────────
#  Herramientas MCP
# ─────────────────────────────────────────────

@mcp.tool()
def listar_portales() -> list[dict]:
    """
    Devuelve los tres portales de sentencias disponibles de la SCBA.
    Usá el campo `clave` como parámetro `portal` en las demás herramientas.
    """
    return [
        {
            "clave":       clave,
            "nombre":      datos["nombre"],
            "url":         datos["url"],
            "descripcion": datos["descripcion"],
        }
        for clave, datos in PORTALES.items()
    ]


@mcp.tool()
def listar_tipos_registro() -> list[dict]:
    """
    Devuelve los tipos de registro disponibles: Resoluciones y Sentencias.
    Usá el campo `valor` como parámetro `tipo_registro` en `buscar_documentos`.
    """
    return [
        {"numero": 1, "nombre": "Resoluciones", "valor": "resoluciones"},
        {"numero": 2, "nombre": "Sentencias",   "valor": "sentencias"},
    ]


@mcp.tool()
def listar_organismos(
    tipo_registro: str = "sentencias",
    portal: str = PORTAL_DEFAULT,
) -> list[str]:
    """
    Devuelve la lista completa de organismos judiciales disponibles para el
    portal y tipo de registro indicados.

    Parámetros:
        tipo_registro — "sentencias" o "resoluciones" (default: "sentencias").
        portal        — "primera_instancia", "camara" o "corte" (default: "primera_instancia").

    Llamá a esta herramienta antes de buscar documentos para conocer los nombres
    exactos de los organismos disponibles.
    """
    if portal not in PORTALES:
        raise ValueError(f"Portal inválido: '{portal}'. Opciones: {list(PORTALES.keys())}")
    if tipo_registro not in ("sentencias", "resoluciones"):
        raise ValueError("tipo_registro debe ser 'sentencias' o 'resoluciones'")

    driver, wait = _get_driver(portal)

    _seleccionar_tipo_registro(wait, tipo_registro)

    wait.until(EC.element_to_be_clickable((By.ID, "select2-Organismos-container"))).click()
    _pausa(1, 2)

    elementos = driver.find_elements(By.XPATH, "//li[contains(@class,'select2-results__option')]")
    organismos = [e.text.strip() for e in elementos if e.text.strip() and e.text.strip() != "---"]

    try:
        driver.find_element(By.ID, "select2-Organismos-container").click()
    except Exception:
        pass

    return organismos


@mcp.tool()
def buscar_documentos(
    organismo: str,
    fecha_desde: str,
    fecha_hasta: str,
    texto_busqueda: str,
    tipo_registro: str = "sentencias",
    portal: str = PORTAL_DEFAULT,
    max_paginas: int = 3,
    max_documentos: int = 20,
) -> dict:
    """
    Busca sentencias o resoluciones en el portal indicado de la SCBA y devuelve
    el texto completo de los documentos encontrados.

    Parámetros:
        organismo       — Nombre exacto del organismo (obtenido con listar_organismos).
        fecha_desde     — Fecha inicial en formato DD/MM/AAAA.
        fecha_hasta     — Fecha final en formato DD/MM/AAAA.
        texto_busqueda  — Palabra o frase a buscar dentro del texto.
        tipo_registro   — "sentencias" o "resoluciones" (default: "sentencias").
        portal          — "primera_instancia", "camara" o "corte" (default: "primera_instancia").
        max_paginas     — Máximo de páginas a recorrer (default: 3).
        max_documentos  — Máximo de documentos a retornar (default: 20).
    """
    if portal not in PORTALES:
        return {"error": f"Portal inválido: '{portal}'. Opciones: {list(PORTALES.keys())}"}
    if not _validar_fecha(fecha_desde):
        return {"error": f"Fecha desde inválida: '{fecha_desde}'. Use DD/MM/AAAA"}
    if not _validar_fecha(fecha_hasta):
        return {"error": f"Fecha hasta inválida: '{fecha_hasta}'. Use DD/MM/AAAA"}
    if tipo_registro not in ("sentencias", "resoluciones"):
        return {"error": "tipo_registro debe ser 'sentencias' o 'resoluciones'"}

    driver, wait = _get_driver(portal)
    documentos: list[dict] = []
    errores: list[str] = []

    try:
        # 1. Tipo de registro
        _seleccionar_tipo_registro(wait, tipo_registro)

        # 2. Organismo
        wait.until(EC.element_to_be_clickable((By.ID, "select2-Organismos-container"))).click()
        _pausa(1, 2)
        xpath_org = (
            f"//li[contains(@class,'select2-results__option') "
            f"and normalize-space(text())='{organismo}']"
        )
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath_org))).click()
        _pausa()

        # 3. Fechas
        campo_desde = wait.until(EC.element_to_be_clickable((By.ID, "idFeDesde")))
        _escribir_lento(campo_desde, fecha_desde)
        _pausa()

        campo_hasta = wait.until(EC.element_to_be_clickable((By.ID, "idFeHasta")))
        _escribir_lento(campo_hasta, fecha_hasta)
        _pausa()

        # 4. Texto
        campo_texto = wait.until(EC.element_to_be_clickable((By.ID, "idTexto")))
        campo_texto.clear()
        campo_texto.send_keys(texto_busqueda)
        _pausa()

        # 5. Buscar
        wait.until(EC.element_to_be_clickable((By.ID, "btnBuscar"))).click()
        wait.until(EC.presence_of_element_located((By.ID, "grid-ListadoRegistros")))
        time.sleep(5)

        # 6. Iterar páginas
        pagina = 1
        while pagina <= max_paginas and len(documentos) < max_documentos:
            try:
                botones = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//button[contains(text(),'Documento')]")
                    )
                )
            except Exception:
                break

            if not botones:
                break

            for i in range(len(botones)):
                if len(documentos) >= max_documentos:
                    break
                try:
                    bots = wait.until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, "//button[contains(text(),'Documento')]")
                        )
                    )
                    if i >= len(bots):
                        break

                    bots[i].click()
                    time.sleep(2)

                    texto = _extraer_texto_modal(driver)
                    parrafos = [p for p in texto.strip().split("\n") if p.strip()]
                    titulo = (
                        _limpiar_nombre(parrafos[1])
                        if len(parrafos) > 1
                        else f"doc_p{pagina}_{i+1}"
                    )

                    documentos.append({
                        "titulo":    titulo,
                        "contenido": texto,
                        "pagina":    pagina,
                        "indice":    i + 1,
                        "portal":    PORTALES[portal]["nombre"],
                    })

                    _cerrar_modal(driver)
                    time.sleep(3)

                except Exception as exc:
                    errores.append(f"Pág {pagina}, doc {i+1}: {str(exc)[:120]}")
                    continue

            # Siguiente página
            try:
                sig = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#grid-ListadoRegistros_next a.page-link")
                ))
                li_padre = sig.find_element(By.XPATH, "./..")
                if "disabled" in (li_padre.get_attribute("class") or ""):
                    break

                driver.execute_script("arguments[0].scrollIntoView();", sig)
                time.sleep(2)
                sig.click()
                wait.until(EC.staleness_of(botones[0]))
                wait.until(EC.presence_of_element_located((By.ID, "grid-ListadoRegistros")))
                time.sleep(6)
                pagina += 1

            except Exception:
                break

    except Exception as exc:
        errores.append(f"Error general: {str(exc)[:200]}")

    return {
        "total_encontrados": len(documentos),
        "tipo_registro":     tipo_registro,
        "organismo":         organismo,
        "portal":            PORTALES[portal]["nombre"],
        "documentos":        documentos,
        "errores":           errores,
    }


@mcp.tool()
def guardar_documentos_en_disco(
    documentos: list[dict],
    organismo: str,
    tipo_registro: str = "sentencias",
    portal: str = PORTAL_DEFAULT,
    carpeta_base: str = "sentencias judiciales",
) -> dict:
    """
    Guarda una lista de documentos (resultado de buscar_documentos) en disco
    como archivos .txt organizados por portal, tipo de registro y organismo.

    Parámetros:
        documentos    — Lista de dicts con {titulo, contenido} (viene de buscar_documentos).
        organismo     — Nombre del organismo (se usa para la sub-carpeta).
        tipo_registro — "sentencias" o "resoluciones".
        portal        — "primera_instancia", "camara" o "corte".
        carpeta_base  — Carpeta raíz de salida (default: "sentencias judiciales").
    """
    nombre_portal = PORTALES.get(portal, {}).get("nombre", portal)
    nombre_org = re.sub(r'[<>:"/\\|?*]', "", organismo).strip()
    ruta_destino = os.path.join(carpeta_base, nombre_portal, tipo_registro, nombre_org)
    os.makedirs(ruta_destino, exist_ok=True)

    guardados: list[str] = []
    errores: list[str] = []

    for doc in documentos:
        try:
            nombre_archivo = re.sub(
                r'[<>:"/\\|?*]', "", doc.get("titulo", "sin_titulo")
            ).strip()[:150]
            ruta = os.path.join(ruta_destino, f"{nombre_archivo}.txt")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(doc.get("contenido", ""))
            guardados.append(ruta)
        except Exception as exc:
            errores.append(str(exc)[:120])

    return {
        "carpeta":          ruta_destino,
        "archivos_guardados": guardados,
        "total":            len(guardados),
        "errores":          errores,
    }


@mcp.tool()
def cerrar_navegador(portal: str = "todos") -> str:
    """
    Cierra el navegador Chrome del portal indicado.
    Usá portal="todos" para cerrar todos los navegadores abiertos.

    Parámetros:
        portal — "primera_instancia", "camara", "corte" o "todos" (default: "todos").
    """
    if portal == "todos":
        _cerrar_todos()
        return "✔ Todos los navegadores cerrados correctamente."

    if portal not in PORTALES:
        return f"Portal inválido: '{portal}'. Opciones: {list(PORTALES.keys())} o 'todos'."

    _cerrar_driver(portal)
    return f"✔ Navegador del portal '{PORTALES[portal]['nombre']}' cerrado correctamente."


# ─────────────────────────────────────────────
#  Recurso: estado del servidor
# ─────────────────────────────────────────────

@mcp.resource("scba://estado")
def estado_servidor() -> str:
    """Estado actual del servidor MCP y los navegadores abiertos."""
    lineas = ["SCBA MCP Server", ""]
    for clave, datos in PORTALES.items():
        nav = "abierto" if clave in _drivers else "cerrado"
        lineas.append(f"[{datos['nombre']}]  {datos['url']}  →  navegador: {nav}")
    lineas += ["", f"Selenium disponible: {SELENIUM_OK}"]
    return "\n".join(lineas)


# ─────────────────────────────────────────────
#  Prompt de ayuda
# ─────────────────────────────────────────────

@mcp.prompt()
def busqueda_guiada(
    tema: str,
    fecha_desde: str = "01/01/2024",
    fecha_hasta: str = "31/12/2024",
    portal: str = PORTAL_DEFAULT,
) -> str:
    """Genera un prompt para que el asistente busque sentencias sobre un tema."""
    nombre_portal = PORTALES.get(portal, {}).get("nombre", portal)
    return (
        f"Quiero buscar sentencias judiciales de la SCBA ({nombre_portal}) "
        f"sobre el tema: '{tema}', entre {fecha_desde} y {fecha_hasta}.\n\n"
        "Por favor:\n"
        "1. Llamá a `listar_organismos` con el portal y tipo_registro correspondiente.\n"
        "2. Seleccioná los organismos más relevantes para el tema.\n"
        "3. Llamá a `buscar_documentos` con los parámetros adecuados.\n"
        "4. Resumí los documentos encontrados de forma clara."
    )


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
