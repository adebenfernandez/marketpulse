"""Construye el paquete de despliegue de las Lambdas: build/lambda.zip (arm64, Python 3.13).

Uso (desde la raíz del proyecto, con el venv activado):
    python scripts/build_lambda.py

Qué mete en el zip:
  - Nuestro código: src/marketpulse/ -> marketpulse/ (sin cachés __pycache__).
  - La configuración: config/watchlist.yaml (Lambda arranca en /var/task, la raíz del zip, así
    que la ruta relativa "config/watchlist.yaml" del código sigue funcionando).
  - Las dependencias de pyproject.toml QUE NO TRAE la capa AWS SDK for pandas (requests, PyYAML,
    python-dotenv y las suyas), compiladas para Linux arm64 y con las MISMAS versiones que el
    venv local, que son las que han pasado los tests.

El zip es DETERMINISTA: mismo contenido -> mismos bytes (orden fijo y fecha fija en cada fichero).
Así Terraform solo vuelve a desplegar la Lambda cuando el código o una dependencia cambian.
"""

import base64
import hashlib
import importlib.metadata as metadata
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DEPS_DIR = BUILD / "deps"
ZIP_PATH = BUILD / "lambda.zip"

PYTHON_VERSION = "3.13"
# Etiquetas de "wheel" para Linux arm64. Lambda python3.13 usa Amazon Linux 2023 (glibc 2.34),
# así que vale cualquier wheel manylinux hasta glibc 2.28, además del clásico manylinux2014
PLATFORMS = ["manylinux2014_aarch64", "manylinux_2_28_aarch64"]

# Lo que ya trae la capa AWS SDK for pandas (paso 3.1). No se empaqueta: duplicarlo engordaría
# el zip y podría tapar la versión de la capa con otra distinta
LAYER_PROVIDED = {"pandas", "pyarrow", "boto3"}

# Límites oficiales de Lambda: 50 MB el zip subido directamente; 250 MB descomprimido
# sumando función y capas
MAX_ZIP_MB = 50
MAX_UNZIPPED_MB = 250
FIXED_DATE = (1980, 1, 1, 0, 0, 0)  # la fecha más antigua que admite el formato zip


def normalize(name: str) -> str:
    """'PyYAML', 'pyyaml' y 'python_dotenv' son el mismo paquete para pip (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    """'requests>=2.32  # comentario' -> 'requests'."""
    return re.match(r"[A-Za-z0-9._-]+", requirement.strip()).group()


def runtime_requirements() -> list[str]:
    """Dependencias de pyproject.toml, sin las de la capa y sin las de desarrollo."""
    with open(ROOT / "pyproject.toml", "rb") as f:
        deps = tomllib.load(f)["project"]["dependencies"]
    return [
        requirement_name(d) for d in deps if normalize(requirement_name(d)) not in LAYER_PROVIDED
    ]


def pinned_closure(names: list[str]) -> dict[str, str]:
    """Las dependencias y las dependencias de estas, con la versión instalada en el venv local.

    Ejemplo: requests -> requests, urllib3, idna, certifi, charset-normalizer. Se fija la versión
    exacta (==) de todas: en Lambda tiene que ir lo mismo que ha pasado los tests en local.
    """
    pins: dict[str, str] = {}
    pending = list(names)
    while pending:
        name = pending.pop()
        key = normalize(name)
        if key in pins:
            continue
        try:
            pins[key] = metadata.version(name)
        except metadata.PackageNotFoundError:
            # Solo pasa con dependencias condicionadas a otro sistema (p. ej. "; sys_platform ==
            # 'win32'") que no están instaladas aquí. Si una de verdad faltara, pip lo diría
            print(f"  aviso: {name} no está instalado en el venv; no se fija su versión")
            continue
        for req in metadata.requires(name) or []:
            if "extra ==" not in req:  # las dependencias opcionales ("extras") no hacen falta
                pending.append(requirement_name(req))
    return pins


def install_dependencies(pins: dict[str, str]) -> None:
    """pip descarga los wheels de Linux arm64 de PyPI y los instala en build/deps/."""
    shutil.rmtree(DEPS_DIR, ignore_errors=True)  # carpeta generada: se rehace siempre de cero
    platform_args = [arg for p in PLATFORMS for arg in ("--platform", p)]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(DEPS_DIR),  # instalar en una carpeta, no en el venv
            *platform_args,  # para Linux arm64, no para este Windows
            "--python-version",
            PYTHON_VERSION,
            "--implementation",
            "cp",  # CPython, el intérprete de Lambda
            "--only-binary=:all:",  # solo wheels ya compilados: nada se compila aquí
            # Sin cachés .pyc: llevan la hora de instalación y cambiarían el RECORD de
            # cada paquete en cada construcción (el zip dejaría de ser determinista)
            "--no-compile",
            "--no-deps",  # ya pasamos la lista completa y fijada
            "--quiet",
            *[f"{name}=={version}" for name, version in sorted(pins.items())],
        ],
        check=True,  # si pip falla, el script se para con error
    )


def files_to_package() -> list[tuple[Path, str]]:
    """(fichero local, ruta dentro del zip), en orden alfabético."""
    entries: list[tuple[Path, str]] = []

    def add_tree(base: Path, prefix: str, skip_top: set[str] = frozenset()) -> None:
        for path in base.rglob("*"):
            rel = path.relative_to(base)
            if not path.is_file() or rel.parts[0] in skip_top:
                continue
            if "__pycache__" in rel.parts or path.suffix == ".pyc":
                continue  # Python regenera las cachés; las de Windows no sirven en Linux
            if path.name == "RECORD" and path.parent.name.endswith(".dist-info"):
                # Inventario que pip usa para desinstalar. Incluye la huella de los .exe que
                # pip genera en Windows (con la hora dentro): cambiaría en cada construcción
                continue
            entries.append((path, f"{prefix}{rel.as_posix()}"))

    add_tree(DEPS_DIR, "", skip_top={"bin"})  # bin/: ejecutables de consola que no usamos
    add_tree(ROOT / "src" / "marketpulse", "marketpulse/")
    entries.append((ROOT / "config" / "watchlist.yaml", "config/watchlist.yaml"))
    return sorted(entries, key=lambda e: e[1])


def write_zip(entries: list[tuple[Path, str]]) -> None:
    ZIP_PATH.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in entries:
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)  # fecha fija: zip determinista
            info.external_attr = 0o644 << 16  # permisos Unix rw-r--r--: Lambda debe poder leerlo
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())


def verify_zip() -> dict:
    """Comprobaciones antes de dar el zip por bueno. Lanza AssertionError si algo no cuadra."""
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        unzipped = sum(i.file_size for i in zf.infolist())
    required = [
        "marketpulse/ingest/handler.py",
        "marketpulse/transform/handler.py",
        "config/watchlist.yaml",
        "requests/__init__.py",
        "yaml/__init__.py",
        "dotenv/__init__.py",
    ]
    missing = [r for r in required if r not in names]
    assert not missing, f"Faltan en el zip: {missing}"

    top_level = {n.split("/")[0] for n in names}
    leaked = top_level & LAYER_PROVIDED
    assert not leaked, f"El zip incluye librerías de la capa: {leaked}"

    # Cualquier librería compilada tiene que ser para Linux arm64 (nunca Windows ni x86)
    binaries = [n for n in names if n.endswith((".so", ".pyd", ".dll"))]
    wrong = [n for n in binaries if not n.endswith(".so") or "x86_64" in n or "win" in n]
    assert not wrong, f"Binarios que no son de Linux arm64: {wrong}"

    zip_mb = ZIP_PATH.stat().st_size / 1e6
    assert zip_mb < MAX_ZIP_MB, f"Zip de {zip_mb:.1f} MB: supera {MAX_ZIP_MB} MB"
    assert unzipped / 1e6 < MAX_UNZIPPED_MB
    return {"files": len(names), "zip_mb": zip_mb, "unzipped_mb": unzipped / 1e6, "so": binaries}


def main() -> int:
    requirements = runtime_requirements()
    pins = pinned_closure(requirements)
    print(f"Dependencias para Lambda ({PLATFORMS[0]}, Python {PYTHON_VERSION}):")
    for name, version in sorted(pins.items()):
        print(f"  {name}=={version}")

    install_dependencies(pins)
    write_zip(files_to_package())
    info = verify_zip()

    digest = hashlib.sha256(ZIP_PATH.read_bytes()).digest()
    print(
        f"Zip: {ZIP_PATH.relative_to(ROOT)} | {info['files']} ficheros | "
        f"{info['zip_mb']:.2f} MB comprimido | {info['unzipped_mb']:.2f} MB descomprimido"
    )
    print(f"Binarios compilados: {info['so'] or 'ninguno'}")
    # Este valor es el que Terraform calculará con filebase64sha256() para saber si ha cambiado
    print(f"SHA-256 (base64): {base64.b64encode(digest).decode()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
