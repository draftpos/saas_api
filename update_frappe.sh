#!/usr/bin/env bash
set -e

echo "======================================"
echo "🚀 Starting Frappe Bench Update & Migration"
echo "======================================"

# Path to your bench
BENCH_PATH="/home/frappe/frappe-bench"

cd "$BENCH_PATH" || {
  echo "❌ Bench directory not found: $BENCH_PATH"
  exit 1
}

echo "📦 Bench path: $(pwd)"

# Optional: ensure correct user
if [ "$(whoami)" != "frappe" ]; then
  echo "⚠️ Warning: Script not running as frappe user"
fi

# Pull latest changes for all apps, apply patches
echo "🔄 Fetching updates for all apps..."
bench update --pull --patch --no-backup

# Run migrations for all sites
echo "🔁 Running migrations on all sites..."
bench --site all migrate

# Restart services
echo "🔄 Restarting bench services..."
bench restart

echo "✅ Bench update and migrations completed successfully"
echo "======================================"
