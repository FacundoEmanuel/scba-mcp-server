# SCBA MCP Server — Sentencias de la Suprema Corte de Buenos Aires

Convierte el buscador de [sentencias.scba.gov.ar](https://sentencias.scba.gov.ar) en un **servidor MCP (Model Context Protocol)** para que Claude Desktop, Claude Code u otro cliente compatible pueda buscar y leer sentencias y resoluciones judiciales directamente desde el chat, sin salir de la conversación.

---

## ¿Qué hace?

Una vez conectado, podés pedirle a Claude cosas como:

> *"Buscá sentencias del Juzgado Civil Nº 7 de Lomas de Zamora que digan notifíquese entre el 20 y el 26 de mayo de 2026"*

Claude va a:
1. Llamar a `listar_organismos` para verificar el nombre exacto del juzgado
2. Llamar a `buscar_documentos` con los parámetros correctos
3. Resumirte y/o guardar en disco los documentos encontrados

---

## Requisitos

- Python 3.9+
- Google Chrome instalado
- `chromedriver` compatible con tu versión de Chrome → [descargar acá](https://googlechromelabs.github.io/chrome-for-testing/)

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/scba-mcp-server.git
cd scba-mcp-server

# 2. Instalar dependencias
pip install mcp selenium
```

> **Nota sobre chromedriver:** copiá el ejecutable (`chromedriver.exe` en Windows, `chromedriver` en Mac/Linux) en la misma carpeta del proyecto, o agregalo al PATH del sistema.

---

## Configuración en Claude Desktop

1. Encontrá tu archivo de configuración:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Agregá el siguiente bloque dentro de `"mcpServers"` (ajustá la ruta):

```json
{
  "mcpServers": {
    "scba-sentencias": {
      "command": "python",
      "args": ["C:/ruta/a/tu/proyecto/scba_mcp_server.py"]
    }
  }
}
```

> En **Mac/Linux** usá la ruta Unix: `"/home/usuario/scba-mcp-server/scba_mcp_server.py"`

3. Reiniciá Claude Desktop.

El archivo `claude_desktop_config.json` incluido en este repositorio es un ejemplo comentado que podés usar de referencia.

---

## Herramientas disponibles

| Herramienta | Descripción |
|---|---|
| `listar_tipos_registro` | Devuelve los tipos disponibles: Sentencias / Resoluciones |
| `listar_organismos` | Devuelve todos los organismos judiciales disponibles |
| `buscar_documentos` | Busca y devuelve el texto completo de los documentos |
| `guardar_documentos_en_disco` | Guarda los resultados como archivos `.txt` organizados por carpetas |
| `cerrar_navegador` | Libera el navegador Chrome al terminar |

### Parámetros de `buscar_documentos`

| Parámetro | Tipo | Descripción |
|---|---|---|
| `organismo` | str | Nombre exacto del organismo (obtenido con `listar_organismos`) |
| `fecha_desde` | str | Fecha inicial en formato `DD/MM/AAAA` |
| `fecha_hasta` | str | Fecha final en formato `DD/MM/AAAA` |
| `texto_busqueda` | str | Palabra o frase a buscar dentro del texto |
| `tipo_registro` | str | `"sentencias"` o `"resoluciones"` (default: `"sentencias"`) |
| `max_paginas` | int | Máximo de páginas de resultados a recorrer (default: `3`) |
| `max_documentos` | int | Máximo de documentos a retornar (default: `20`) |

---

## Probar con MCP Inspector

```bash
npx @modelcontextprotocol/inspector python scba_mcp_server.py
```

Abrí [http://localhost:6274](http://localhost:6274) y explorá las herramientas de forma interactiva.

---

## Estructura de carpetas generada por `guardar_documentos_en_disco`

```
sentencias judiciales/
├── sentencias/
│   └── JUZGADO EN LO CIVIL Y COMERCIAL Nº 7 - LOMAS DE ZAMORA/
│       ├── Córdoba Julio c Avila Carlos - Daños y Perjuicios.txt
│       └── Banco Provincia c Deyser SRL - Cobro Ejecutivo.txt
└── resoluciones/
    └── JUZGADO EN LO CIVIL Y COMERCIAL Nº 1 - LA PLATA/
        └── Resolución_Z.txt
```

---

## Notas técnicas

- El scraper usa **pausas aleatorias** entre requests para no sobrecargar el servidor de la SCBA.
- El navegador Chrome corre en modo **headless** (sin ventana visible).
- `max_paginas` y `max_documentos` en `buscar_documentos` permiten limitar los resultados y evitar sesiones demasiado largas.
- El driver Chrome es un **singleton**: se abre una sola vez y se reutiliza entre llamadas. Llamá a `cerrar_navegador` cuando termines.

---

## Limitaciones

- Depende del sitio web de la SCBA: si cambian el HTML o la estructura del buscador, el scraper puede necesitar ajustes.
- Requiere Chrome instalado localmente; no funciona en entornos sin interfaz gráfica sin el modo headless activado (ya está activado por defecto).

---

## Licencia

MIT — libre para usar, modificar y distribuir.
