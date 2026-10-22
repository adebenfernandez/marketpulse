"""Construye el paquete de despliegue de las Lambdas: build/lambda.zip (arm64, Python 3.13).

Uso (desde la raíz del proyecto, con el venv activado):
    python scripts/build_lambda.py                # construye el zip
    python scripts/build_lambda.py --update-lock  # actualiza config/lambda-requirements.txt

Qué mete en el zip:
  - Nuestro código: src/marketpulse/ -> marketpulse/ (sin cachés __pycache__).
  - La configuración: config/watchlist.yaml (Lambda arranca en /var/task, la raíz del zip, así
    que la ruta relativa "config/watchlist.yaml" del código sigue funcionando).
  - Las dependencias de pyproject.toml QUE NO TRAE la capa AWS SDK for pandas (requests, PyYAML,
    python-dotenv y las suyas), compiladas para Linux arm64 y con las versiones EXACTAS de
    config/lambda-requirements.txt (se genera desde el venv local, que es el que pasa los tests).

El zip es DETERMINISTA y REPRODUCIBLE: el mismo commit da los mismos bytes en cualquier máquina
(Windows o el Linux de CodeBuild): orden fijo, fecha fija, versiones del fichero de bloqueo y
finales de línea LF en nuestro código. Así Terraform solo vuelve a desplegar la Lambda cuando el
código o una dependencia cambian de verdad (paso 6.7).
"""

import base64
import hashlib
import importlib.metadata as metadata
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
ZIP_PATH = BUILD / "lambda.zip"  # solo el zip final vive en el proyecto (y en OneDrive)

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

# Versiones exactas de las dependencias de la Lambda. Sin este fichero, cada máquina fijaba las
# de su propio venv, y CodeBuild empaquetaba otro certifi que Windows (paso 6.7)
LOCK_PATH = ROOT / "config" / "lambda-requirements.txt"

# Ficheros de texto NUESTROS que se normalizan a finales de línea LF al empaquetarlos. Git entrega
# CRLF en Windows (core.autocrlf) y LF en Linux; sin normalizar, el zip cambiaba de huella según
# dónde se construyera (paso 6.7). Python y YAML leen igual las dos formas
TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".txt"}


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


def write_lock(pins: dict[str, str], path: Path = LOCK_PATH) -> None:
    """Escribe el fichero de bloqueo: una línea nombre==versión por dependencia, en orden."""
    header = (
        "# Dependencias de la Lambda con versión EXACTA (las empaqueta scripts/build_lambda.py).\n"
        "# Se generan desde el venv local: python scripts/build_lambda.py --update-lock\n"
    )
    lines = [f"{name}=={version}" for name, version in sorted(pins.items())]
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def read_lock(path: Path = LOCK_PATH) -> dict[str, str]:
    """Lee el fichero de bloqueo (ignora comentarios y líneas vacías)."""
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, version = line.split("==")
            pins[normalize(name)] = version.strip()
    return pins


def check_lock_covers(locked: dict[str, str], needed: set[str]) -> None:
    """El bloqueo debe tener EXACTAMENTE los paquetes que piden las dependencias de pyproject.

    Si se añade o se quita una dependencia en pyproject.toml y no se regenera el bloqueo, se para
    con un mensaje claro (si no, la Lambda saldría sin un paquete o con uno que sobra).
    """
    missing, extra = needed - set(locked), set(locked) - needed
    if missing or extra:
        raise SystemExit(
            f"config/lambda-requirements.txt no está al día (faltan {sorted(missing)}, "
            f"sobran {sorted(extra)}): ejecuta python scripts/build_lambda.py --update-lock"
        )


def install_dependencies(pins: dict[str, str], target: Path) -> None:
    """pip descarga los wheels de Linux arm64 de PyPI y los instala en build/deps/."""
    platform_args = [arg for p in PLATFORMS for arg in ("--platform", p)]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(target),  # instalar en una carpeta, no en el venv
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


def files_to_package(deps_dir: Path) -> list[tuple[Path, str]]:
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

    add_tree(deps_dir, "", skip_top={"bin"})  # bin/: ejecutables de consola que no usamos
    add_tree(ROOT / "src" / "marketpulse", "marketpulse/")
    entries.append((ROOT / "config" / "watchlist.yaml", "config/watchlist.yaml"))
    return sorted(entries, key=lambda e: e[1])


def packaged_bytes(path: Path, arcname: str) -> bytes:
    """Contenido de un fichero tal y como va al zip: nuestro texto, siempre con finales LF."""
    data = path.read_bytes()
    ours = arcname.startswith(("marketpulse/", "config/"))
    if ours and path.suffix in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return data


def write_zip(entries: list[tuple[Path, str]], zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in entries:
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)  # fecha fija: zip determinista
            info.external_attr = 0o644 << 16  # permisos Unix rw-r--r--: Lambda debe poder leerlo
            # "Sistema que creó el fichero": Python pone 0 (MS-DOS) en Windows y 3 (Unix) en Linux,
            # y cambiaba la huella del zip según dónde se construyera (paso 6.7). Siempre Unix,
            # coherente con los permisos Unix de la línea anterior
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, packaged_bytes(path, arcname))


def verify_zip(zip_path: Path) -> dict:
    """Comprobaciones antes de dar el zip por bueno. Lanza AssertionError si algo no cuadra."""
    with zipfile.ZipFile(zip_path) as zf:
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

    zip_mb = zip_path.stat().st_size / 1e6
    assert zip_mb < MAX_ZIP_MB, f"Zip de {zip_mb:.1f} MB: supera {MAX_ZIP_MB} MB"
    assert unzipped / 1e6 < MAX_UNZIPPED_MB
    return {"files": len(names), "zip_mb": zip_mb, "unzipped_mb": unzipped / 1e6, "so": binaries}


def main(argv: list[str]) -> int:
    venv_pins = pinned_closure(runtime_requirements())
    if "--update-lock" in argv:
        write_lock(venv_pins)
        print(f"Actualizado {LOCK_PATH.relative_to(ROOT)} con las versiones del venv")
        return 0

    pins = read_lock()
    check_lock_covers(pins, set(venv_pins))  # mismos paquetes; las versiones mandan las del bloqueo
    print(f"Dependencias para Lambda ({PLATFORMS[0]}, Python {PYTHON_VERSION}), desde el bloqueo:")
    for name, version in sorted(pins.items()):
        print(f"  {name}=={version}")

    # Todo el trabajo intermedio va a una carpeta temporal del sistema, FUERA de OneDrive: una
    # carpeta build/deps dentro del proyecto se quedó bloqueada por la sincronización ("Acceso
    # denegado") y pip no pudo instalar nada (paso 4.2). Cada construcción empieza de cero
    with tempfile.TemporaryDirectory(prefix="marketpulse-build-") as tmp:
        deps_dir, tmp_zip = Path(tmp) / "deps", Path(tmp) / "lambda.zip"
        install_dependencies(pins, deps_dir)
        write_zip(files_to_package(deps_dir), tmp_zip)
        info = verify_zip(
            tmp_zip
        )  # si falla, se lanza AssertionError y el zip anterior sigue intacto
        BUILD.mkdir(exist_ok=True)
        # Solo un zip YA VERIFICADO sustituye al anterior. os.replace es atómico porque solo
        # RENOMBRA, y renombrar solo funciona dentro del mismo disco: en CodeBuild /tmp es otro
        # disco ("Invalid cross-device link", paso 6.6). Por eso primero se copia a un temporal
        # junto al destino (mismo disco) y después se renombra
        staged = ZIP_PATH.with_suffix(".zip.tmp")
        shutil.copyfile(tmp_zip, staged)
        os.replace(staged, ZIP_PATH)

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
    sys.exit(main(sys.argv[1:]))
