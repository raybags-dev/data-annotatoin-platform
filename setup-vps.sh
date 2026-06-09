#!/usr/bin/env bash
# setup-vps.sh — first-time VPS setup for the data annotation platform
# Run this ONCE before the first GitHub Actions deploy.
# After that, GitHub Actions handles all future deploys automatically.
set -euo pipefail

VPS_HOST="89.167.74.127"
VPS_USER="root"
VPS_KEY="$HOME/.ssh/portfolio_base"
VPS_DIR="/opt/data-annotation-platform"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CYAN="\033[36m" GREEN="\033[32m" RED="\033[31m" RESET="\033[0m"
step() { echo -e "\n${CYAN}→ $*${RESET}"; }
ok()   { echo -e "${GREEN}✓ $*${RESET}"; }
die()  { echo -e "${RED}✗ $*${RESET}" >&2; exit 1; }

# ── Guard: .env must have real credentials ───────────────────────────────────
if grep -q "REPLACE_WITH" "$REPO_ROOT/.env" 2>/dev/null; then
  die ".env still contains placeholder values. Fill in SUPABASE_SERVICE_KEY first."
fi

# ── 1. Check SSH connectivity ─────────────────────────────────────────────────
step "Testing SSH connection to $VPS_USER@$VPS_HOST"
ssh -i "$VPS_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
    "$VPS_USER@$VPS_HOST" "echo OK" || die "Cannot connect to VPS"
ok "SSH connection OK"

# ── 2. Create app directory on VPS ───────────────────────────────────────────
step "Creating $VPS_DIR on VPS"
ssh -i "$VPS_KEY" "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_DIR"
ok "Directory created"

# ── 3. Copy .env to VPS ──────────────────────────────────────────────────────
step "Copying .env to VPS (secrets stay on server, not in git)"
scp -i "$VPS_KEY" "$REPO_ROOT/.env" "$VPS_USER@$VPS_HOST:$VPS_DIR/.env"
ok ".env deployed to $VPS_DIR/.env"

# ── 4. Ensure Docker is installed ────────────────────────────────────────────
step "Verifying Docker on VPS"
ssh -i "$VPS_KEY" "$VPS_USER@$VPS_HOST" \
  "docker --version && docker compose version" || \
  die "Docker not found on VPS — install Docker + Docker Compose plugin first"
ok "Docker verified"

# ── 5. Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════${RESET}"
echo -e "${GREEN} VPS setup complete                     ${RESET}"
echo -e "${GREEN}════════════════════════════════════════${RESET}"
echo ""
echo "  Next: push to main to trigger the first automated deploy:"
echo "    ./deploy-all.sh"
echo ""
echo "  After first deploy, pull the Ollama model (one-time):"
echo "    ssh -i ~/.ssh/portfolio_base root@$VPS_HOST \\"
echo "      'docker exec \$(docker ps -qf name=ollama) ollama pull llama3.2:3b'"
