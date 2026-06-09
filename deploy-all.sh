#!/usr/bin/env bash
# deploy-all.sh — one-command deploy: syntax check → commit → push → CI/CD pipeline
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

CYAN="\033[36m" GREEN="\033[32m" RED="\033[31m" YELLOW="\033[33m" RESET="\033[0m"
step()  { echo -e "\n${CYAN}→ $*${RESET}"; }
ok()    { echo -e "${GREEN}✓ $*${RESET}"; }
warn()  { echo -e "${YELLOW}⚠ $*${RESET}"; }
die()   { echo -e "${RED}✗ $*${RESET}" >&2; exit 1; }

# ── 1. Syntax check ──────────────────────────────────────────────────────────
step "Syntax check (Python)"
python3 -m py_compile \
  backend/app/main.py \
  backend/app/core/config.py \
  backend/app/core/database.py \
  backend/app/pipeline/orchestrator.py || die "Python syntax error — fix before deploying"
ok "Python syntax clean"

# ── 2. Stage all changes ─────────────────────────────────────────────────────
step "Staging changes"
git add -A

if git diff --cached --quiet; then
  warn "No changes to commit — pushing current HEAD"
else
  COMMIT_MSG="${1:-deploy: $(date '+%Y-%m-%d %H:%M') [auto]}"
  git commit -m "$COMMIT_MSG

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
  ok "Committed: $COMMIT_MSG"
fi

# ── 3. Push → triggers GitHub Actions ────────────────────────────────────────
step "Pushing to origin main"
git push origin main
ok "Pushed"

# ── 4. Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════${RESET}"
echo -e "${GREEN} Deploy triggered successfully          ${RESET}"
echo -e "${GREEN}════════════════════════════════════════${RESET}"
echo ""
echo "  Monitor CI/CD:"
echo "    https://github.com/raybags-dev/data-annotatoin-platform/actions"
echo ""
echo "  After deploy, services:"
echo "    Backend API docs: http://89.167.74.127:8001/docs"
echo "    Frontend:         http://89.167.74.127:5174"
echo ""
echo "  First deploy only — pull Ollama model on VPS:"
echo "    ssh root@89.167.74.127 \\"
echo "      'docker exec \$(docker ps -qf name=ollama) ollama pull llama3.2:3b'"
