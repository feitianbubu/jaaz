#!/bin/bash
set -e

# This script runs as root (because ENTRYPOINT runs as root by default)
# Change ownership of the mounted volume to the 'app' user
chown -R app:app /app || true

# Now, execute the original CMD as the user specified by the USER instruction in the Dockerfile
# The "$@" expands to the arguments passed to the entrypoint (which are the CMD arguments)
exec "$@"