# SCBA MCP Server — Sentencias de la Suprema Corte de Buenos Aires

Convierte los tres portales de sentencias de la SCBA en un **servidor MCP (Model Context Protocol)** para que Claude Desktop, Claude Code u otro cliente compatible pueda buscar y leer sentencias y resoluciones judiciales directamente desde el chat.

| Portal | URL |
|---|---|
| Primera Instancia | sentencias.scba.gov.ar |
| Cámaras de Apelación | sentencias-camara.scba.gov.ar |
| Corte Suprema | sentencias-corte.scba.gov.ar |

---

## ¿Qué hace?

Una vez conectado, podés pedirle a Claude cosas como:

> *"Buscá sentencias de la Cámara de Apelaciones de La Plata sobre contratos de alquiler entre enero y marzo de 2026"*

> *"Buscá en la Corte Suprema resoluciones que digan 'inconstitucional' del último mes"*

> *"Buscá sentencias del Juzgado Civil Nº 7 de Lomas de Zamora que digan notifíquese esta semana"*

Claude va a:
1. Llamar a `listar_organismos` con el portal correcto para verificar el nombre exacto
2. Llamar a `buscar_documentos` con los parámetros adecuados
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
git clone https://github.com/FacundoEmanuel/scba-mcp-server.git
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

3. Reiniciá Claude Desktop.

---

## Herramientas disponibles

| Herramienta | Descripción |
|---|---|
| `listar_portales` | Devuelve los 3 portales disponibles con sus URLs |
| `listar_tipos_registro` | Devuelve los tipos disponibles: Sentencias / Resoluciones |
| `listar_organismos` | Devuelve todos los organismos del portal indicado |
| `buscar_documentos` | Busca y devuelve el texto completo de los documentos |
| `guardar_documentos_en_disco` | Guarda los resultados como archivos `.txt` organizados por carpetas |
| `cerrar_navegador` | Cierra uno o todos los navegadores Chrome abiertos |

### Portales disponibles (`portal`)

| Clave | Nombre | URL |
|---|---|---|
| `primera_instancia` | Primera Instancia | sentencias.scba.gov.ar |
| `camara` | Cámaras de Apelación | sentencias-camara.scba.gov.ar |
| `corte` | Corte Suprema | sentencias-corte.scba.gov.ar |

### Parámetros de `buscar_documentos`

| Parámetro | Tipo | Descripción |
|---|---|---|
| `organismo` | str | Nombre exacto del organismo (obtenido con `listar_organismos`) |
| `fecha_desde` | str | Fecha inicial en formato `DD/MM/AAAA` |
| `fecha_hasta` | str | Fecha final en formato `DD/MM/AAAA` |
| `texto_busqueda` | str | Palabra o frase a buscar dentro del texto |
| `portal` | str | `"primera_instancia"`, `"camara"` o `"corte"` (default: `"primera_instancia"`) |
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
├── Primera Instancia/
│   └── sentencias/
│       └── JUZGADO EN LO CIVIL Y COMERCIAL Nº 7 - LOMAS DE ZAMORA/
│           └── Córdoba Julio c Avila Carlos - Daños y Perjuicios.txt
├── Cámaras de Apelación/
│   └── sentencias/
│       └── CÁMARA DE APELACIÓN - LA PLATA/
│           └── González c Municipalidad.txt
└── Corte Suprema/
    └── resoluciones/
        └── SUPREMA CORTE/
            └── Resolución_Z.txt
```

---

## Notas técnicas

- El servidor abre **un navegador Chrome por portal** (singleton por portal), reutilizándolo entre llamadas.
- El scraper usa **pausas aleatorias** entre requests para no sobrecargar los servidores de la SCBA.
- El navegador Chrome corre en modo **headless** (sin ventana visible).
- Usá `cerrar_navegador(portal="todos")` al terminar para liberar todos los recursos.

---

## Limitaciones

- Depende del sitio web de la SCBA: si cambian el HTML o la estructura del buscador, el scraper puede necesitar ajustes.
- Requiere Chrome instalado localmente.

---

## Licencia

MIT — libre para usar, modificar y distribuir.
