#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   source ./scripts/use_env.sh local
#   source ./scripts/use_env.sh prod
#
# Nota: debe ser "source" (o ".") para que las variables queden en tu shell actual.

usage() {
  echo "Uso: source ./scripts/use_env.sh {local|prod}" >&2
  exit 2
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "ERROR: Ejecuta esto con source, por ejemplo:" >&2
  echo "  source ./scripts/use_env.sh local" >&2
  exit 2
fi

TARGET="${1:-}"
if [[ "$TARGET" != "local" && "$TARGET" != "prod" ]]; then
  usage
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILE="$ROOT/.env.$TARGET"

if [[ ! -f "$FILE" ]]; then
  echo "ERROR: No existe $FILE" >&2
  echo "Crea el archivo copiando la plantilla:" >&2
  if [[ "$TARGET" == "local" ]]; then
    echo "  cp .env.local.example .env.local" >&2
  else
    echo "  cp .env.prod.example .env.prod" >&2
  fi
  return 2
fi

set -a
# shellcheck disable=SC1090
source "$FILE"
set +a

echo "OK: variables cargadas desde $FILE" >&2
