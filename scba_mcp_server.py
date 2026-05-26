"""
SCBA MCP Server — Suprema Corte de Buenos Aires
Expone el scraper de sentencias.scba.gov.ar como herramientas MCP
para que cualquier IA compatible (Claude Desktop, Cursor, etc.) pueda
buscar y leer sentencias y resoluciones judiciales.

Instalación:
    pip install mcp selenium

Uso con Claude Desktop  →  ver claude_desktop_config.json
Uso con MCP Inspector   →  python scba_mcp_server.py
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
#  Instancia del servidor MCP
# ─────────────────────────────────────────────
mcp = FastMCP(
    "SCBA Sentencias",
    instructions=(
        "Servidor de sentencias judiciales de la Suprema Corte de Buenos Aires. "
        "Permite buscar resoluciones y sentencias por organismo, rango de fechas y "
        "texto libre. Siempre llama primero a `listar_organismos` para obtener los "
        "organismos disponibles antes de buscar documentos."
    ),
)


# ─────────────────────────────────────────────
#  Estado global del navegador (singleton)
# ─────────────────────────────────────────────
_driver: Optional[webdriver.Chrome] = None
_wait: Optional[WebDriverWait] = None

TIEMPO_ESPERA_MIN = 2
TIEMPO_ESPERA_MAX = 4
BASE_URL = "https://sentencias.scba.gov.ar/"


def _pausa(min_t: float = TIEMPO_ESPERA_MIN, max_t: float = TIEMPO_ESPERA_MAX) -> None:
    time.sleep(random.uniform(min_t, max_t))


def _get_driver() -> tuple[webdriver.Chrome, WebDriverWait]:
    """Devuelve el driver singleton, iniciándolo si es necesario."""
    global _driver, _wait

    if not SELENIUM_OK:
        raise RuntimeError(
            "Selenium no está instalado. Ejecutá: pip install selenium"
        )

    if _driver is None:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Si tenés chromedriver en PATH no hace falta especificar executable_path
        try:
            s = Service(executable_path="chromedriver.exe")
            _driver = webdriver.Chrome(service=s, options=options)
        except Exception:
            _driver = webdriver.Chrome(options=options)

        _wait = WebDriverWait(_driver, 30)
        _driver.get(BASE_URL)
        time.sleep(5)

    return _driver, _wait  # type: ignore[return-value]


def _cerrar_driver() -> None:
    global _driver, _wait
    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
        _wait = None


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
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Cerrar')]"))).click()
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


# ─────────────────────────────────────────────
#  Herramientas MCP
# ─────────────────────────────────────────────

@mcp.tool()
def listar_organismos(tipo_registro: str = "sentencias") -> list[str]:
    """
    Devuelve la lista completa de organismos judiciales disponibles en el buscador
    de sentencias.scba.gov.ar para el tipo de registro indicado.

    Parámetros:
        tipo_registro — "sentencias" o "resoluciones" (default: "sentencias").
                        Es obligatorio seleccionarlo primero para que el sitio
                        cargue los organismos correspondientes.

    Llamá a esta herramienta antes de buscar documentos para conocer los nombres
    exactos de los organismos que podés usar como parámetro en `buscar_documentos`.
    """
    if tipo_registro not in ("sentencias", "resoluciones"):
        raise ValueError("tipo_registro debe ser 'sentencias' o 'resoluciones'")

    driver, wait = _get_driver()

    # ── PASO 1: seleccionar el tipo de registro primero
    #    (el sitio solo carga los organismos después de esta selección)
    wait.until(EC.element_to_be_clickable((By.ID, "select2-Registros-container"))).click()
    _pausa(1, 2)

    opciones_reg = wait.until(
        EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class,'select2-results__option')]"))
    )
    opciones_visibles = [o for o in opciones_reg if o.text.strip()]

    # índice 1 = Resoluciones, índice 2 = Sentencias (el índice 0 es el placeholder)
    idx_reg = 1 if tipo_registro == "resoluciones" else 2
    if idx_reg < len(opciones_visibles):
        opciones_visibles[idx_reg].click()
    _pausa()

    # ── PASO 2: ahora sí abrir el dropdown de organismos (ya está cargado)
    wait.until(EC.element_to_be_clickable((By.ID, "select2-Organismos-container"))).click()
    _pausa(1, 2)

    elementos = driver.find_elements(By.XPATH, "//li[contains(@class,'select2-results__option')]")
    organismos = [e.text.strip() for e in elementos if e.text.strip() and e.text.strip() != "---"]

    # Cerrar el dropdown sin seleccionar nada
    try:
        driver.find_element(By.ID, "select2-Organismos-container").click()
    except Exception:
        pass

    return organismos


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
def buscar_documentos(
    organismo: str,
    fecha_desde: str,
    fecha_hasta: str,
    texto_busqueda: str,
    tipo_registro: str = "sentencias",
    max_paginas: int = 3,
    max_documentos: int = 20,
) -> dict:
    """
    Busca sentencias o resoluciones en el buscador oficial de la SCBA y devuelve
    el texto completo de cada documento encontrado.

    Parámetros:
        organismo       — Nombre exacto del organismo (usar `listar_organismos`).
        fecha_desde     — Fecha inicio en formato DD/MM/AAAA.
        fecha_hasta     — Fecha fin en formato DD/MM/AAAA.
        texto_busqueda  — Palabras clave a buscar en el texto de las resoluciones.
        tipo_registro   — "sentencias" o "resoluciones" (default: "sentencias").
        max_paginas     — Número máximo de páginas a recorrer (default: 3).
        max_documentos  — Número máximo de documentos a retornar (default: 20).

    Retorna un dict con:
        - total_encontrados: cantidad de documentos descargados
        - tipo_registro: tipo de registro consultado
        - organismo: organismo consultado
        - documentos: lista de dicts con {titulo, contenido, pagina, indice}
        - errores: lista de mensajes de error si los hubo
    """
    # ── Validaciones
    if not _validar_fecha(fecha_desde):
        return {"error": f"Fecha desde inválida: '{fecha_desde}'. Use DD/MM/AAAA"}
    if not _validar_fecha(fecha_hasta):
        return {"error": f"Fecha hasta inválida: '{fecha_hasta}'. Use DD/MM/AAAA"}
    if tipo_registro not in ("sentencias", "resoluciones"):
        return {"error": "tipo_registro debe ser 'sentencias' o 'resoluciones'"}

    driver, wait = _get_driver()
    documentos: list[dict] = []
    errores: list[str] = []

    try:
        # ── 1. Seleccionar tipo de registro
        wait.until(EC.element_to_be_clickable((By.ID, "select2-Registros-container"))).click()
        _pausa(1, 2)

        opciones_reg = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class,'select2-results__option')]"))
        )
        opciones_visibles = [o for o in opciones_reg if o.text.strip()]

        # índice 1 = Resoluciones, índice 2 = Sentencias
        idx_reg = 1 if tipo_registro == "resoluciones" else 2
        if idx_reg < len(opciones_visibles):
            opciones_visibles[idx_reg].click()
        _pausa()

        # ── 2. Seleccionar organismo
        wait.until(EC.element_to_be_clickable((By.ID, "select2-Organismos-container"))).click()
        _pausa(1, 2)

        xpath_org = (
            f"//li[contains(@class,'select2-results__option') "
            f"and normalize-space(text())='{organismo}']"
        )
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath_org))).click()
        _pausa()

        # ── 3. Fechas
        campo_desde = wait.until(EC.element_to_be_clickable((By.ID, "idFeDesde")))
        _escribir_lento(campo_desde, fecha_desde)
        _pausa()

        campo_hasta = wait.until(EC.element_to_be_clickable((By.ID, "idFeHasta")))
        _escribir_lento(campo_hasta, fecha_hasta)
        _pausa()

        # ── 4. Texto
        campo_texto = wait.until(EC.element_to_be_clickable((By.ID, "idTexto")))
        campo_texto.clear()
        campo_texto.send_keys(texto_busqueda)
        _pausa()

        # ── 5. Buscar
        wait.until(EC.element_to_be_clickable((By.ID, "btnBuscar"))).click()
        wait.until(EC.presence_of_element_located((By.ID, "grid-ListadoRegistros")))
        time.sleep(5)

        # ── 6. Iterar páginas
        pagina = 1
        while pagina <= max_paginas and len(documentos) < max_documentos:
            try:
                botones = wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, "//button[contains(text(),'Documento')]"))
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
                        EC.presence_of_all_elements_located((By.XPATH, "//button[contains(text(),'Documento')]"))
                    )
                    if i >= len(bots):
                        break

                    bots[i].click()
                    time.sleep(2)

                    texto = _extraer_texto_modal(driver)
                    parrafos = [p for p in texto.strip().split("\n") if p.strip()]
                    titulo = _limpiar_nombre(parrafos[1]) if len(parrafos) > 1 else f"doc_p{pagina}_{i+1}"

                    documentos.append({
                        "titulo":    titulo,
                        "contenido": texto,
                        "pagina":    pagina,
                        "indice":    i + 1,
                    })

                    _cerrar_modal(driver)
                    time.sleep(3)

                except Exception as exc:
                    msg = f"Pág {pagina}, doc {i+1}: {str(exc)[:120]}"
                    errores.append(msg)
                    continue

            # ── Siguiente página
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
        "documentos":        documentos,
        "errores":           errores,
    }


@mcp.tool()
def guardar_documentos_en_disco(
    documentos: list[dict],
    organismo: str,
    tipo_registro: str = "sentencias",
    carpeta_base: str = "sentencias judiciales",
) -> dict:
    """
    Guarda una lista de documentos (resultado de `buscar_documentos`) en disco
    como archivos .txt organizados por tipo de registro y organismo.

    Parámetros:
        documentos    — Lista de dicts con {titulo, contenido} (viene de buscar_documentos).
        organismo     — Nombre del organismo (se usa para la sub-carpeta).
        tipo_registro — "sentencias" o "resoluciones".
        carpeta_base  — Carpeta raíz de salida (default: "sentencias judiciales").

    Retorna un dict con archivos guardados y posibles errores.
    """
    nombre_org = re.sub(r'[<>:"/\\|?*]', "", organismo).strip()
    ruta_destino = os.path.join(carpeta_base, tipo_registro, nombre_org)
    os.makedirs(ruta_destino, exist_ok=True)

    guardados: list[str] = []
    errores: list[str] = []

    for doc in documentos:
        try:
            nombre_archivo = re.sub(r'[<>:"/\\|?*]', "", doc.get("titulo", "sin_titulo")).strip()[:150]
            ruta = os.path.join(ruta_destino, f"{nombre_archivo}.txt")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(doc.get("contenido", ""))
            guardados.append(ruta)
        except Exception as exc:
            errores.append(str(exc)[:120])

    return {
        "carpeta": ruta_destino,
        "archivos_guardados": guardados,
        "total": len(guardados),
        "errores": errores,
    }


@mcp.tool()
def cerrar_navegador() -> str:
    """
    Cierra el navegador Chrome que el servidor abrió para el scraping.
    Llamá a esta herramienta cuando hayas terminado de buscar documentos
    para liberar recursos del sistema.
    """
    _cerrar_driver()
    return "✔ Navegador cerrado correctamente."


# ─────────────────────────────────────────────
#  Recurso: estado del servidor
# ─────────────────────────────────────────────

@mcp.resource("scba://estado")
def estado_servidor() -> str:
    """Estado actual del servidor MCP y el navegador."""
    nav = "abierto" if _driver is not None else "cerrado"
    return (
        f"SCBA MCP Server\n"
        f"URL base: {BASE_URL}\n"
        f"Navegador: {nav}\n"
        f"Selenium disponible: {SELENIUM_OK}\n"
    )


# ─────────────────────────────────────────────
#  Prompt de ayuda
# ─────────────────────────────────────────────

@mcp.prompt()
def busqueda_guiada(tema: str, fecha_desde: str = "01/01/2024", fecha_hasta: str = "31/12/2024") -> str:
    """Genera un prompt para que el asistente busque sentencias sobre un tema."""
    return (
        f"Quiero buscar sentencias judiciales de la SCBA sobre el tema: '{tema}', "
        f"entre {fecha_desde} y {fecha_hasta}.\n\n"
        "Por favor:\n"
        "1. Llamá a `listar_organismos` con el tipo_registro correspondiente para ver los organismos disponibles.\n"
        "2. Seleccioná los organismos más relevantes para el tema.\n"
        "3. Llamá a `buscar_documentos` con los parámetros adecuados.\n"
        "4. Resumí los documentos encontrados de forma clara."
    )


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # stdio → para Claude Desktop / Claude Code
    # Para MCP Inspector usá: mcp.run(transport="streamable-http")
    mcp.run(transport="stdio")
