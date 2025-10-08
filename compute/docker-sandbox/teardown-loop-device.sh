#!/bin/bash
# Teardown script to remove loop device filesystem
# Run this to clean up the loop device setup

set -e

# Configuration (must match setup script)
LOOP_IMAGE_PATH="${LOOP_IMAGE_PATH:-/var/lib/agent-workspace.img}"
MOUNT_POINT="${MOUNT_POINT:-/mnt/agent-workspace}"

echo "Removing loop device filesystem for agent workspace"
echo "===================================================="
echo "Image path: $LOOP_IMAGE_PATH"
echo "Mount point: $MOUNT_POINT"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Unmount if mounted
if mount | grep -q "$MOUNT_POINT"; then
    echo "Unmounting $MOUNT_POINT..."
    umount "$MOUNT_POINT"
else
    echo "✓ Not mounted"
fi

# Remove mount point
if [ -d "$MOUNT_POINT" ]; then
    echo "Removing mount point..."
    rmdir "$MOUNT_POINT"
else
    echo "✓ Mount point doesn't exist"
fi

# Remove from fstab
if grep -q "$LOOP_IMAGE_PATH" /etc/fstab; then
    echo "Removing entry from /etc/fstab..."
    grep -v "$LOOP_IMAGE_PATH" /etc/fstab > /tmp/fstab.tmp
    mv /tmp/fstab.tmp /etc/fstab
else
    echo "✓ No entry in /etc/fstab"
fi

# Remove loop device image
if [ -f "$LOOP_IMAGE_PATH" ]; then
    echo "Removing loop device image..."
    rm -f "$LOOP_IMAGE_PATH"
else
    echo "✓ Loop device image doesn't exist"
fi

echo ""
echo "✓ Loop device teardown complete!"