#!/usr/bin/env bash
# shellcheck shell=bash

# ============================================
# Script para ejecutar el módulo API-Fútbol
# - Interactivo y por flags
# - Robusto, con validaciones y colores
# ============================================

set -Eeuo pipefail

# ---------- Configuración ----------
APP_DIR="C:\Dev\projects\rebuild-api-football\backend"
DEFAULT_LIMIT=5
PY_MIN_MAJOR=3
PY_MIN_MINOR=9

# Permite sobrescribir el binario de Python
PYTHON_BIN="${PYTHON_BIN:-}"

# Reporte por defecto (para --tests)
REPORT_KIND="none"      # none | html | html-standalone
NO_SUGAR="false"        # true => pytest sin pytest-sugar (salida clásica)

# Colores
if [[ -t 1 ]]; then
  RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"; BLUE="\033[34m"; BOLD="\033[1m"; NC="\033[0m"
else
  RED=""; GREEN=""; YELLOW=""; BLUE=""; BOLD=""; NC=""
fi

# ---------- Utilidades ----------
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

ensure_dir() { [[ -d "$1" ]] || mkdir -p "$1"; }

cleanup() {
  # Lugar para limpiar recursos si fuera necesario
  :
}
trap 'err "Falló la ejecución en línea ${BASH_LINENO[0]}"; cleanup' ERR
trap 'warn "Interrumpido por el usuario"; exit 130' INT

usage() {
  cat <<EOF
${BOLD}MÓDULO API-FÚTBOL${NC}

Uso:
  $(basename "$0")                     # Modo interactivo
  $(basename "$0") --tests             # Ejecuta tests (sin reporte por defecto)
  $(basename "$0") --tests --report html
  $(basename "$0") --tests --report html-standalone
  $(basename "$0") --tests --no-sugar
  $(basename "$0") --all [-y|--yes]
  $(basename "$0") --limit N
  $(basename "$0") --league ID
  $(basename "$0") --stats
  $(basename "$0") --help

Opciones:
  --tests                 Ejecuta los tests automatizados.
  --report KIND           Tipo de reporte para --tests:
                             • html              → Genera reports/pytest_report.html
                             • html-standalone   → HTML auto‑contenido (un solo archivo)
                           Ejemplo:
                             $(basename "$0") --tests --report html
  --no-sugar              Ejecuta pytest sin el plugin pytest-sugar (salida clásica)

  --all                   Procesa TODAS las ligas (toma horas).
  -y, --yes               Omite confirmación al usar --all.
  --limit N               Procesa N ligas (modo prueba). Por defecto: ${DEFAULT_LIMIT}.
  --league ID             Procesa una liga específica (ID numérico).
  --stats                 Muestra estadísticas de la base de datos.
  --help                  Muestra esta ayuda.

Variables de entorno:
  PYTHON_BIN              Ruta al binario de Python (ej: /usr/bin/python3).
                          Si no se define, se intentará python3 y luego python.
EOF
}

# ---------- Manejo temprano de --help (evita side-effects) ----------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

# Detecta el binario de Python y verifica versión
detect_python() {
  if [[ -n "$PYTHON_BIN" ]]; then
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
      err "PYTHON_BIN apunta a un binario inexistente: $PYTHON_BIN"
      exit 1
    fi
  else
    if command -v python3 >/dev/null 2>&1; then
      PYTHON_BIN="python3"
    elif command -v python >/dev/null 2>&1; then
      PYTHON_BIN="python"
    else
      err "No se encontró un binario de Python (python3 o python) en PATH."
      exit 1
    fi
  fi

  # Verificar versión mínima
  local ver
  ver="$("$PYTHON_BIN" - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
)"
  IFS='.' read -r MAJ MIN PATCH <<<"$ver"
  if (( MAJ < PY_MIN_MAJOR )) || { (( MAJ == PY_MIN_MAJOR )) && (( MIN < PY_MIN_MINOR )); }; then
    err "Se requiere Python >= ${PY_MIN_MAJOR}.${PY_MIN_MINOR}, encontrado ${ver} en ${PYTHON_BIN}"
    exit 1
  fi
  ok "Usando ${PYTHON_BIN} (Python ${ver})"
}

activate_venv() {
  # Activa venv si existe
  if [[ -f "venv/bin/activate" ]]; then
    #shellcheck source=/dev/null
    source "venv/bin/activate"
    ok "Entorno virtual venv activado"
    PYTHON_BIN="python"
  fi
}

enter_app_dir() {
  if [[ ! -d "$APP_DIR" ]]; then
    err "Directorio no encontrado: $APP_DIR"
    exit 1
  fi
  cd "$APP_DIR"
  ok "Directorio actual: $(pwd)"
}

confirm() {
  local msg="$1"
  local auto="${2:-false}"
  if [[ "$auto" == "true" ]]; then
    return 0
  fi
  read -r -p "$msg (s/n): " ans
  if [[ "$ans" != "s" && "$ans" != "S" ]]; then
    warn "Operación cancelada por el usuario."
    return 1
  fi
  return 0
}

# ---------- Acciones ----------
run_tests() {
  info "Ejecutando tests..."
  local pytest_opts="-q"
  [[ "$NO_SUGAR" == "true" ]] && pytest_opts="$pytest_opts -p no:sugar"

  case "$REPORT_KIND" in
    none)
      "$PYTHON_BIN" -m pytest $pytest_opts || "$PYTHON_BIN" test_api_football.py
      ;;
    html)
      ensure_dir "reports"
      info "Generando reporte HTML: reports/pytest_report.html"
      "$PYTHON_BIN" -m pytest $pytest_opts --html=reports/pytest_report.html || "$PYTHON_BIN" test_api_football.py
      ;;
    html-standalone)
      ensure_dir "reports"
      info "Generando reporte HTML auto-contenido: reports/pytest_report.html"
      "$PYTHON_BIN" -m pytest $pytest_opts --html=reports/pytest_report.html --self-contained-html || "$PYTHON_BIN" test_api_football.py
      ;;
    *)
      err "Tipo de reporte no soportado: $REPORT_KIND"
      return 2
      ;;
  esac
}

process_all() {
  local assume_yes="${1:-false}"
  info "Procesar TODAS las ligas."
  if confirm "¿Estás seguro? Esto puede tomar varias horas." "$assume_yes"; then
    "$PYTHON_BIN" -m api_football.main
  else
    return 1
  fi
}

process_limit() {
  local n="$1"
  if [[ ! "$n" =~ ^[0-9]+$ ]] || (( n <= 0 )); then
    err "Valor inválido para --limit: $n (debe ser entero > 0)"
    exit 1
  fi
  info "Procesando ${n} ligas (modo prueba)..."
  "$PYTHON_BIN" -m api_football.main --limit "$n"
}

process_league() {
  local league_id="$1"
  if [[ ! "$league_id" =~ ^[0-9]+$ ]]; then
    err "ID de liga inválido: $league_id (solo dígitos)"
    exit 1
  fi
  info "Procesando liga ${league_id}..."
  "$PYTHON_BIN" -m api_football.main --league-id "$league_id"
}

show_stats() {
  info "Obteniendo estadísticas..."
  # Recomendado: mover esto a un script Python propio. Temporalmente:
  "$PYTHON_BIN" - <<'PY'
from api_football.db_manager import DatabaseManager

db = DatabaseManager()
if db.connect():
    stats = db.get_statistics()
    print(f'\nTotal partidos: {stats.get("total_partidos", 0)}')
    print(f'Total ligas: {stats.get("total_ligas", 0)}')
    print('\nTop 10 ligas con más partidos:')
    for i, liga in enumerate(stats.get('partidos_por_liga', [])[:10], 1):
        print(f'  {i}. {liga.get("liga_nombre", "N/A")} ({liga.get("_id", "N/A")}): {liga.get("count", 0)} partidos')
    db.close()
else:
    raise SystemExit("No se pudo conectar a la base de datos.")
PY
}

# ---------- Parseo de flags (no interactivo) ----------
if (( $# > 0 )); then
  # 1) Parsear flags SIN ejecutar acciones (permite combinaciones)
  ASSUME_YES="false"
  DO_TESTS="false"; DO_ALL="false"; DO_LIMIT="false"; DO_LEAGUE="false"; DO_STATS="false"
  LIMIT_N="$DEFAULT_LIMIT"; LEAGUE_ID=""

  while (( $# > 0 )); do
    case "$1" in
      --tests) DO_TESTS="true"; shift;;
      --report) REPORT_KIND="${2:-none}"; shift 2;;
      --no-sugar) NO_SUGAR="true"; shift;;
      --all) DO_ALL="true"; if [[ "${2:-}" == "-y" || "${2:-}" == "--yes" ]]; then ASSUME_YES="true"; shift 2; else shift; fi;;
      --limit) DO_LIMIT="true"; LIMIT_N="${2:-$DEFAULT_LIMIT}"; shift 2;;
      --league) DO_LEAGUE="true"; LEAGUE_ID="${2:-}"; shift 2;;
      --stats) DO_STATS="true"; shift;;
      --help|-h) usage; exit 0;;
      *) err "Opción no reconocida: $1"; usage; exit 2;;
    esac
  done

  # 2) Setup (solo si hay algo que ejecutar)
  enter_app_dir
  activate_venv
  detect_python

  # 3) Ejecutar acciones según flags
  [[ "$DO_TESTS" == "true" ]] && run_tests
  [[ "$DO_ALL" == "true" ]] && process_all "$ASSUME_YES"
  [[ "$DO_LIMIT" == "true" ]] && process_limit "$LIMIT_N"
  if [[ "$DO_LEAGUE" == "true" ]]; then
    [[ -z "$LEAGUE_ID" ]] && { err "Falta el ID de liga para --league"; exit 1; }
    process_league "$LEAGUE_ID"
  fi
  [[ "$DO_STATS" == "true" ]] && show_stats
  exit 0
fi

# ---------- Modo interactivo ----------
enter_app_dir
activate_venv
detect_python

echo -e "${BOLD}====================================${NC}"
echo -e "${BOLD}MÓDULO API-FÚTBOL${NC}"
echo -e "${BOLD}====================================${NC}"
echo
echo "Opciones:"
echo "1. Ejecutar tests"
echo "2. Procesar todas las ligas"
echo "3. Procesar ${DEFAULT_LIMIT} ligas (modo prueba)"
echo "4. Procesar una liga específica"
echo "5. Ver estadísticas de la BD"
echo

read -r -p "Selecciona una opción (1-5): " option

case "$option" in
  1)
    echo
    # Submenú de reporte de tests
    echo "Formato de reporte:"
    echo "  1) Sin reporte (consola)"
    echo "  2) HTML"
    echo "  3) HTML auto-contenido"
    read -r -p "Elige (1-3): " rep
    case "$rep" in
      1) REPORT_KIND="none" ;;
      2) REPORT_KIND="html" ;;
      3) REPORT_KIND="html-standalone" ;;
      *) REPORT_KIND="none" ;;
    esac
    run_tests
    ;;
  2)
    echo
    process_all "false" || true
    ;;
  3)
    echo
    process_limit "$DEFAULT_LIMIT"
    ;;
  4)
    echo
    read -r -p "Ingresa el ID de la liga (ej: 140 para La Liga): " league_id
    process_league "$league_id"
    ;;
  5)
    echo
    show_stats
    ;;
  *)
    err "Opción inválida"
    exit 1
    ;;
esac

ok "Finalizado."