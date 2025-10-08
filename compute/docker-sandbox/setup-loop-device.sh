#!/bin/bash
# Setup script for loop device filesystem to limit agent workspace size
# This provides hard disk limits without using tmpfs (which consumes RAM)
# Run this once on the host system (requires root/sudo)

set -e

# Configuration
LOOP_IMAGE_PATH="${LOOP_IMAGE_PATH:-/var/lib/agent-workspace.img}"
MOUNT_POINT="${MOUNT_POINT:-/mnt/agent-workspace}"
SIZE_MB="${SIZE_MB:-2048}"  # Default 2GB

echo "Setting up loop device filesystem for agent workspace"
echo "======================================================="
echo "Image path: $LOOP_IMAGE_PATH"
echo "Mount point: $MOUNT_POINT"
echo "Size: ${SIZE_MB}MB"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Check if already setup
if mount | grep -q "$MOUNT_POINT"; then
    echo "✓ Loop device already mounted at $MOUNT_POINT"
    exit 0
fi

# Create loop device image if it doesn't exist
if [ ! -f "$LOOP_IMAGE_PATH" ]; then
    echo "Creating ${SIZE_MB}MB loop device image at $LOOP_IMAGE_PATH..."
    dd if=/dev/zero of="$LOOP_IMAGE_PATH" bs=1M count="$SIZE_MB" status=progress
    
    echo "Creating ext4 filesystem..."
    mkfs.ext4 -F "$LOOP_IMAGE_PATH"
else
    echo "✓ Loop device image already exists at $LOOP_IMAGE_PATH"
fi

# Create mount point if it doesn't exist
if [ ! -d "$MOUNT_POINT" ]; then
    echo "Creating mount point at $MOUNT_POINT..."
    mkdir -p "$MOUNT_POINT"
else
    echo "✓ Mount point already exists at $MOUNT_POINT"
fi

# Mount the loop device
echo "Mounting loop device..."
mount -o loop,noexec,nodev,nosuid "$LOOP_IMAGE_PATH" "$MOUNT_POINT"

# Set permissions so containers can write
echo "Setting permissions..."
chmod 1777 "$MOUNT_POINT"

# Add to fstab for persistence across reboots
FSTAB_ENTRY="$LOOP_IMAGE_PATH $MOUNT_POINT ext4 loop,noexec,nodev,nosuid,defaults 0 0"
if ! grep -q "$LOOP_IMAGE_PATH" /etc/fstab; then
    echo "Adding entry to /etc/fstab for persistence..."
    echo "$FSTAB_ENTRY" >> /etc/fstab
else
    echo "✓ Entry already exists in /etc/fstab"
fi

# Verify
echo ""
echo "Verification:"
echo "============="
df -h "$MOUNT_POINT"
echo ""
echo "✓ Loop device setup complete!"
echo ""
echo "To use with Docker Compose, add this to your .env file:"
echo "AGENT_WORKSPACE_PATH=$MOUNT_POINT"
echo ""
echo "Or update docker-compose.yml to mount this path:"
echo "  volumes:"
echo "    - $MOUNT_POINT:/app/.agent_workspaces"