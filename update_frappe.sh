#!/usr/bin/env bash
set -e

echo "======================================"
echo "🚀 Starting Targeted Frappe App Update"
echo "======================================"

# Path to your bench
BENCH_PATH="/home/frappe/frappe-bench"
# Comma-separated list of your custom apps
APPS="havano_addons,havano_pos_integration,saas_api"

cd "$BENCH_PATH" || {
  echo "❌ Bench directory not found: $BENCH_PATH"
  exit 1
}

# Optional: ensure correct user
if [ "$(whoami)" != "frappe" ]; then
  echo "⚠️ Warning: Script not running as frappe user. Current user: $(whoami)"
fi

# Update ONLY specified apps
# This skips frappe and erpnext code updates
echo "🔄 Updating specific apps: $APPS"
bench update --apps $APPS --pull --patch --no-backup

# Run migrations for all sites
# This ensures DB schema changes in your apps are applied
echo "🔁 Running migrations on all sites..."
bench --site all migrate

# Restart services to apply changes
echo "🔄 Restarting bench services..."
bench restart

echo "✅ Update and migrations for $APPS completed successfully"
echo "======================================"