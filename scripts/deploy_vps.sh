#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if [ ! -f .env.production ]; then
  echo "Copie .env.production.example para .env.production e configure os valores." >&2
  exit 1
fi

docker compose --env-file .env.production -f compose.prod.yml build
docker compose --env-file .env.production -f compose.prod.yml up -d banco
docker compose --env-file .env.production -f compose.prod.yml run --rm configurador
docker compose --env-file .env.production -f compose.prod.yml up -d
docker compose --env-file .env.production -f compose.prod.yml ps

tentativa=1
while [ "$tentativa" -le 30 ]; do
  if curl --fail --silent http://127.0.0.1:8080/health >/dev/null; then
    echo "Deploy concluido e saudavel."
    exit 0
  fi
  tentativa=$((tentativa + 1))
  sleep 2
done

echo "O deploy iniciou, mas o health check nao respondeu." >&2
docker compose --env-file .env.production -f compose.prod.yml logs --tail=100
exit 1
