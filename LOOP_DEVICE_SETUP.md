# Loop Device Setup for Agent Workspace

## Overview

By default, agent workspaces are created in `.agent_workspaces/` with no hard size limit. To prevent disk exhaustion from runaway agent operations, you can use a loop device to enforce a hard size limit.

## Benefits

- **Hard size limit**: Enforced at filesystem level (e.g., 2GB)
- **No RAM usage**: Unlike tmpfs, uses disk space only
- **Persistent**: Survives container restarts
- **Simple**: No complex quota systems or monitoring

## Setup Instructions

### 1. One-Time Host Setup (requires root)

```bash
# Run the setup script
sudo ./setup-loop-device.sh

# Or manually:
sudo dd if=/dev/zero of=/var/lib/agent-workspace.img bs=1M count=2048  # 2GB
sudo mkfs.ext4 /var/lib/agent-workspace.img
sudo mkdir -p /mnt/agent-workspace
sudo mount -o loop /var/lib/agent-workspace.img /mnt/agent-workspace
sudo chmod 1777 /mnt/agent-workspace

# Make persistent across reboots
echo '/var/lib/agent-workspace.img /mnt/agent-workspace ext4 loop,defaults 0 0' | sudo tee -a /etc/fstab
```

### 2. Enable in Docker Compose

Edit `docker-compose.yml` and uncomment the loop device mount:

```yaml
volumes:
  - ./:/app
  - /var/run/docker.sock:/var/run/docker.sock:ro
  - /mnt/agent-workspace:/app/.agent_workspaces  # <- Uncomment this line
```

### 3. Restart Services

```bash
make down
make up
```

## Verification

Check that the loop device is mounted and has the expected size:

```bash
df -h /mnt/agent-workspace
# Should show: /dev/loop0  2.0G  6.0M  1.9G   1% /mnt/agent-workspace
```

## Customization

You can customize the size and paths by setting environment variables before running the setup script:

```bash
export SIZE_MB=4096  # 4GB instead of 2GB
export MOUNT_POINT=/opt/agent-workspace  # Different mount point
sudo -E ./setup-loop-device.sh
```

## Teardown

To remove the loop device setup:

```bash
sudo ./teardown-loop-device.sh
```

## How It Works

1. **Loop device**: A file (`/var/lib/agent-workspace.img`) acts as a virtual disk
2. **Filesystem**: The file contains an ext4 filesystem with a fixed size
3. **Mount**: The filesystem is mounted at `/mnt/agent-workspace`
4. **Bind mount**: Docker binds this to `/app/.agent_workspaces` in the container
5. **Hard limit**: When the 2GB is exhausted, write operations fail with "No space left on device"

## Security Notes

- The loop device is mounted with `noexec,nodev,nosuid` options for security
- Directory permissions are set to `1777` (sticky bit) so all users can write but only owners can delete
- The size limit prevents any single operation from filling the host disk

## Troubleshooting

### "No space left on device" errors
- Check usage: `df -h /mnt/agent-workspace`
- Clean old workspaces: `sudo rm -rf /mnt/agent-workspace/*`
- Or increase size by re-running setup with larger SIZE_MB

### Permission denied errors
- Ensure the mount point has correct permissions: `sudo chmod 1777 /mnt/agent-workspace`
- Check that your container user matches the host user (see UID/GID settings)

### Mount not persisting across reboots
- Check `/etc/fstab` has the correct entry
- Ensure the loop device image exists at `/var/lib/agent-workspace.img`