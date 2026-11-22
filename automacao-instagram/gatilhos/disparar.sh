#!/usr/bin/env bash
# Dispara o GitHub Actions na hora certa: grava a hora em gatilhos/<alvo>.txt e faz push na main.
#   bash automacao-instagram/gatilhos/disparar.sh story   # story diário (rotina das 8h50)
#   bash automacao-instagram/gatilhos/disparar.sh posts   # posts agendados (rotina das 10h50, ter/sex)
# Sempre parte da main remota atual e envia o próprio commit (HEAD:main). Nunca usa a branch "main" local,
# que na nuvem pode estar velha (foi isso que travou o story de 22/11/2026). Tenta até 5 vezes.
set -u
cd "$(git rev-parse --show-toplevel)" || exit 1
case "${1:-}" in
  story) arq=automacao-instagram/gatilhos/story.txt; msg="Gatilho do story diário" ;;
  posts) arq=automacao-instagram/gatilhos/posts.txt; msg="Gatilho dos posts agendados [gatilho]" ;;
  *) echo "uso: disparar.sh story|posts"; exit 2 ;;
esac
git config user.name >/dev/null 2>&1 || git config user.name "Claude"
git config user.email >/dev/null 2>&1 || git config user.email "noreply@anthropic.com"
for t in 1 2 3 4 5; do
  if git fetch -q origin main && git checkout -q --detach origin/main; then
    date -u +%Y-%m-%dT%H:%M:%SZ > "$arq"
    git add "$arq" && git commit -q -m "$msg"
    if git push -q origin HEAD:main; then
      echo "OK: gatilho '$1' enviado ($(git rev-parse --short HEAD))"
      exit 0
    fi
  fi
  echo "tentativa $t falhou; tentando de novo"
  sleep $((t * 5))
done
echo "FALHOU: não consegui enviar o gatilho '$1'"
exit 1
