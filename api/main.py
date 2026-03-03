"""
JSON Utilities API
Servicio web para consultar, combinar y modificar archivos JSON
almacenados en un directorio local montado como volumen Docker.
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="JSON Utilities API",
    description="API para consultar, combinar y modificar archivos JSON.",
    version="1.0.0",
)

# Ruta donde se montan los JSONs dentro del contenedor
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))


def _resolve_filename(name: str) -> Path:
    """Agrega la extensión .json si no la tiene y devuelve la ruta completa."""
    if not name.endswith(".json"):
        name = f"{name}.json"
    return DATA_DIR / name


def _read_json(filepath: Path) -> dict | list:
    """Lee y parsea un archivo JSON."""
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filepath.name}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"El archivo {filepath.name} no es un JSON válido.")


def _write_json(filepath: Path, data: dict | list) -> None:
    """Escribe datos a un archivo JSON con formato legible."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/files", summary="Listar archivos JSON")
def list_files():
    """Retorna la lista de nombres de archivos .json disponibles en la carpeta de datos."""
    if not DATA_DIR.exists():
        raise HTTPException(status_code=500, detail="El directorio de datos no existe.")

    files = sorted([f.stem for f in DATA_DIR.glob("*.json")])
    return {"count": len(files), "files": files}


@app.get("/files/combine", summary="Combinar archivos JSON")
def combine_files(
    exact_names: Optional[list[str]] = Query(
        default=None,
        description="Nombres exactos de los archivos a combinar (sin extensión .json).",
    ),
    starts_with: Optional[str] = Query(
        default=None,
        description="Prefijo para buscar archivos que comiencen con este texto.",
    ),
):
    """
    Combina múltiples archivos JSON en uno solo.

    Se puede usar `exact_names` para indicar nombres exactos,
    o `starts_with` para seleccionar todos los que empiecen con un prefijo.
    Los diccionarios se fusionan directamente (merge); las listas se concatenan.
    """
    if not exact_names and not starts_with:
        raise HTTPException(
            status_code=400,
            detail="Debes proporcionar 'exact_names' o 'starts_with'.",
        )

    filepaths: list[Path] = []

    if exact_names:
        for name in exact_names:
            filepaths.append(_resolve_filename(name))

    if starts_with:
        matched = sorted(DATA_DIR.glob(f"{starts_with}*.json"))
        if not matched:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron archivos que empiecen con '{starts_with}'.",
            )
        filepaths.extend(matched)

    # Eliminar duplicados conservando el orden
    seen = set()
    unique_paths: list[Path] = []
    for p in filepaths:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(p)

    if not unique_paths:
        raise HTTPException(status_code=400, detail="No se resolvieron archivos para combinar.")

    combined: dict | list = {}
    first_is_list = False

    for i, fp in enumerate(unique_paths):
        data = _read_json(fp)
        if i == 0:
            combined = data
            first_is_list = isinstance(data, list)
        else:
            if first_is_list and isinstance(data, list):
                combined.extend(data)  # type: ignore
            elif isinstance(combined, dict) and isinstance(data, dict):
                combined.update(data)
            else:
                # Tipos mixtos: encapsular todo en una lista
                if not isinstance(combined, list):
                    combined = [combined]
                combined.append(data)  # type: ignore

    return {
        "sources": [p.stem for p in unique_paths],
        "combined": combined,
    }


@app.get("/files/{filename}", summary="Leer un archivo JSON")
def read_file(filename: str):
    """
    Retorna el contenido de un archivo JSON.
    No es necesario incluir la extensión `.json` en el nombre.
    """
    filepath = _resolve_filename(filename)
    data = _read_json(filepath)
    return {"filename": filepath.stem, "data": data}


@app.post("/files/{filename}/add", summary="Agregar datos a un archivo JSON")
def add_to_file(filename: str, payload: dict):
    """
    Agrega datos a un archivo JSON existente.

    - Si el archivo contiene un **diccionario**, las llaves del payload
      se fusionan (las llaves existentes se sobreescriben con los nuevos valores).
    - Si el archivo contiene una **lista**, el payload se añade al final.
    """
    filepath = _resolve_filename(filename)
    data = _read_json(filepath)

    if isinstance(data, dict):
        data.update(payload)
    elif isinstance(data, list):
        data.append(payload)
    else:
        raise HTTPException(status_code=500, detail="Formato de JSON no soportado para esta operación.")

    _write_json(filepath, data)
    return {"message": f"Datos agregados exitosamente a {filepath.stem}.", "data": data}
