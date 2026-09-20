#!/usr/bin/env bash
# Ensure Goodix-Touchscreen re-probes if the boot-time I2C probe failed.
# Fallback: Goodix-TS Treiber neu an den i2c-Client binden (benoetigt root).
set -u
DRIVER_DIR=/sys/bus/i2c/drivers/Goodix-TS
CLIENT=10-005d

for i in $(seq 1 30); do
    if grep -qs "Goodix" /proc/bus/input/devices; then
        echo "Goodix Touchscreen aktiv (Versuch $i)"
        exit 0
    fi
    if [ -e "$DRIVER_DIR/bind" ]; then
        echo "$CLIENT" > "$DRIVER_DIR/bind" 2>/dev/null || true
    fi
    sleep 2
done
echo "WARNUNG: Goodix Touchscreen nach 60 s nicht erkannt" >&2
exit 1