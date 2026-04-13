#!/bin/sh
# Export all current environment variables so cron jobs inherit them.
# This writes them to /etc/environment which cron reads on Debian/Ubuntu.
printenv | grep -v "^_=" > /etc/environment
exec "$@"
