#!/usr/bin/env bash

echo "======================================"
echo "🚀 Starting Targeted Frappe App Update"
echo "======================================"

BENCH_PATH="/home/frappe/frappe-bench"
APPS="havano_addons,havano_pos_integration,saas_api"
FAILED_SITES=()

cd "$BENCH_PATH" || {
  echo "❌ Bench directory not found: $BENCH_PATH"
  exit 1
}

# Warn if not frappe user
if [ "$(whoami)" != "frappe" ]; then
  echo "⚠️ Warning: Script not running as frappe user (current: $(whoami))"
fi

# ------------------------------------------------
# Update specific apps only
# ------------------------------------------------
echo "🔄 Updating apps: $APPS"
if ! bench update --apps "$APPS" --pull --patch --no-backup; then
  echo "❌ App update failed — aborting"
  exit 1
fi

# ------------------------------------------------
# Migrate sites ONE BY ONE (failure-tolerant)
# ------------------------------------------------
echo "🔁 Migrating sites individually..."

SITES=$(bench list-sites)

for site in $SITES; do
  echo "➡️ Migrating site: $site"

  if bench --site "$site" migrate; then
    echo "✅ Migration successful: $site"
  else
    echo "❌ Migration FAILED: $site"
    FAILED_SITES+=("$site")
    echo "➡️ Continuing to next site..."
  fi

  echo "--------------------------------------"
done

# ------------------------------------------------
# Restart services
# ------------------------------------------------
echo "🔄 Restarting bench services..."
bench restart

# ------------------------------------------------
# Summary
# ------------------------------------------------
echo "======================================"
if [ ${#FAILED_SITES[@]} -gt 0 ]; then
  echo "⚠️ Migration completed with failures"
  echo "❌ Failed sites:"
  for s in "${FAILED_SITES[@]}"; do
    echo "  - $s"
  done
else
  echo "✅ All sites migrated successfully"
fi
echo "======================================"
