#!/bin/sh
# Export all current environment variables so cron jobs inherit them.
# Restrict to root-only read to protect secrets (tokens, keys).
printenv | grep -v "^_=" > /etc/environment
chmod 600 /etc/environment
exec "$@"
