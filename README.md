# SCBA MCP Server — Sentencias de la Suprema Corte de Buenos Aires

Convierte el scraper de `sentencias.scba.gov.ar` en un **servidor MCP** para
que Claude Desktop, Claude Code u otro cliente MCP pueda buscar y leer
sentencias y resoluciones judiciales directamente desde el chat.

---

## Instalación

```bash
pip install mcp selenium
```

> Necesitás **chromedriver** compatible con tu versión de Chrome:
> https://googlechromelabs.github.io/chrome-for-testing/

---

## Configuración en Claude Desktop

1. Encontrá tu archivo de configuración:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Agregá el bloque del archivo `claude_desktop_config.json` (ajustá la ruta):

```json
{
  "mcpServers": {
    "scba-sentencias": {
      "command": "python",
      "args": ["C:/TU_RUTA/scba_mcp_server.py"]
    }
  }
}
```

3. Reiniciá Claude Desktop.

---

## Herramientas disponibles

| Herramienta | Descripción |
|---|---|
| `listar_tipos_registro` | Devuelve los tipos: Sentencias / Resoluciones |
| `listar_organismos` | Devuelve todos los organismos disponibles |
| `buscar_documentos` | Busca y retorna el texto de documentos |
| `guardar_documentos_en_disco` | Guarda los resultados como archivos .txt |
| `cerrar_navegador` | Libera el navegador Chrome |

---

## Ejemplo de uso desde Claude

Una vez conectado el servidor podés pedirle a Claude:

> "Buscá sentencias de la Cámara de Apelaciones de La Plata sobre
> contratos de alquiler entre el 01/01/2024 y el 31/12/2024"

Claude va a:
1. Llamar a `listar_organismos` para verificar el nombre exacto
2. Llamar a `buscar_documentos` con los parámetros correctos
3. Resumirte los documentos encontrados

---

## Probar con MCP Inspector

```bash
# Instalá el inspector
npx @modelcontextprotocol/inspector python scba_mcp_server.py
```

Abrí http://localhost:6274 y explorá las herramientas.

---

## Estructura de carpetas generada

```
sentencias judiciales/
├── sentencias/
│   └── Cámara de Apelaciones La Plata/
│       ├── Caso_X.txt
│       └── Caso_Y.txt
└── resoluciones/
    └── Juzgado Civil Nro 1/
        └── Resolución_Z.txt
```

---

## Notas

- El scraper usa pausas aleatorias para no sobrecargar el servidor de la SCBA.
- `max_paginas` y `max_documentos` en `buscar_documentos` limitan la cantidad
  de resultados para evitar requests excesivos.
- El navegador Chrome se abre en modo **headless** (sin ventana visible).
