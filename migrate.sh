#!/usr/bin/env bash
# migrate.sh — verify Supabase tables exist and connection is live
# Tables must be created by running supabase_migrations.sql in the Supabase SQL Editor:
#   https://supabase.com/dashboard/project/hxkxoduptzlbdkgpdstp/sql
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CYAN="\033[36m" GREEN="\033[32m" RED="\033[31m" RESET="\033[0m"
step() { echo -e "\n${CYAN}→ $*${RESET}"; }
ok()   { echo -e "${GREEN}✓ $*${RESET}"; }
die()  { echo -e "${RED}✗ $*${RESET}" >&2; exit 1; }

step "Checking Supabase connection and tables"

cd "$REPO_ROOT/backend"
python3 - <<'PYEOF'
import asyncio, sys

async def check():
    from app.core.database import connect_db, get_db
    try:
        await connect_db()
    except Exception as e:
        print(f"FAIL: Cannot connect to Supabase — {e}", file=sys.stderr)
        sys.exit(1)

    db = get_db()

    # Check ann_datasets
    try:
        r = await db.table("ann_datasets").select("id", count="exact").execute()
        print(f"  ann_datasets  OK  ({r.count} rows)")
    except Exception as e:
        print(f"  ann_datasets  MISSING — run supabase_migrations.sql first\n  Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Check ann_records
    try:
        r = await db.table("ann_records").select("id", count="exact").execute()
        print(f"  ann_records   OK  ({r.count} rows)")
    except Exception as e:
        print(f"  ann_records   MISSING — run supabase_migrations.sql first\n  Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Check storage bucket
    from supabase import create_client
    from app.core.config import settings
    sc = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    buckets = [b.name for b in sc.storage.list_buckets()]
    if settings.SUPABASE_BUCKET in buckets:
        print(f"  {settings.SUPABASE_BUCKET}  OK  (Supabase Storage bucket)")
    else:
        print(f"  bucket '{settings.SUPABASE_BUCKET}' NOT FOUND — create it in Supabase Storage", file=sys.stderr)
        sys.exit(1)

asyncio.run(check())
PYEOF

echo ""
echo -e "${GREEN}✓ All Supabase resources verified — ready to deploy${RESET}"
echo ""
echo "  Run ./deploy-all.sh to push and trigger CI/CD"
