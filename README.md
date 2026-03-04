# JSON Utilities API

API con FastAPI para consultar, combinar y modificar archivos JSON almacenados localmente, todo dentro de un contenedor Docker.

## Estructura

```
json-utilities/
├── docker-compose.yml
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
└── data/                    ← Archivos JSON (subcarpetas soportadas)
    ├── Carpeta1/
    │   ├── archivo1.json
    │   └── archivo2.json
    └── Carpeta2/
        └── archivo3.json
```

## Inicio rápido

```bash
# Levantar
docker compose up -d --build

# Detener
docker compose down
```

La API estará disponible en `http://localhost:8000`.
Documentación interactiva (Swagger): `http://localhost:8000/docs`

## Endpoints

### `GET /files` — Listar archivos

Retorna todos los JSON disponibles con su ruta relativa (sin extensión).

```
GET /files
→ {"count": 3, "files": ["Carpeta1/archivo1", "Carpeta1/archivo2", "Carpeta2/archivo3"]}
```

### `GET /files/{ruta}` — Leer un archivo

Retorna el contenido de un JSON. No necesitas incluir `.json`.

```
GET /files/Carpeta1/archivo1
→ {"filename": "Carpeta1/archivo1", "data": {"clave": "valor", ...}}
```

### `GET /files/combine` — Combinar archivos

Combina múltiples JSON en uno solo. Acepta dos tipos de filtro (pueden usarse juntos):

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| `exact_names` | Nombres exactos (repetible) | `?exact_names=Carpeta1/archivo1&exact_names=Carpeta1/archivo2` |
| `starts_with` | Prefijos de ruta (repetible) | `?starts_with=Carpeta1/&starts_with=Carpeta2` |

```
GET /files/combine?starts_with=Carpeta1/archivo
→ {"sources": ["Carpeta1/archivo1", "Carpeta1/archivo2"], "combined": {...}}
```

### `POST /files/{ruta}/add` — Agregar datos

Envía un JSON en el body para fusionarlo con el archivo existente.

- **Diccionarios**: se hace merge de las llaves.
- **Listas**: se añade el payload al final.

```
POST /files/Carpeta1/archivo1/add
Body: {"NuevoElemento": "nuevo.png"}
→ {"message": "Datos agregados exitosamente a Carpeta1/archivo1.", "data": {...}}
```
