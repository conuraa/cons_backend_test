#!/bin/bash
# Apply phone update patches to cons_backend
# Run on the server: bash /path/to/apply_patches.sh

set -e

BACKEND_DIR="/home/sada/cons_backend/FastAPI"

echo "=== Backing up files ==="
cp "$BACKEND_DIR/services/onec_client.py" "$BACKEND_DIR/services/onec_client.py.bak"
cp "$BACKEND_DIR/routers/clients.py" "$BACKEND_DIR/routers/clients.py.bak"
echo "Backups created (.bak files)"

echo ""
echo "=== Applying patch to services/onec_client.py ==="
cd /tmp
python3 /tmp/patch_onec_client.py

echo ""
echo "=== Applying patch to routers/clients.py ==="
python3 /tmp/patch_clients.py

echo ""
echo "=== Done! ==="
echo "To restart the container: docker restart cons_api"
echo "To check logs: docker logs -f cons_api --tail=50"
echo ""
echo "To rollback:"
echo "  cp $BACKEND_DIR/services/onec_client.py.bak $BACKEND_DIR/services/onec_client.py"
echo "  cp $BACKEND_DIR/routers/clients.py.bak $BACKEND_DIR/routers/clients.py"
echo "  docker restart cons_api"
