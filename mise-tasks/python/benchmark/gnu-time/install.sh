#!/usr/bin/env bash
#MISE description="Install GNU time required for actual RSS and CPU measurements on the Linux benchmark runner"
set -euo pipefail

if [ "$(uname -s)" != Linux ]; then
	echo "GNU time is installed only on Linux; skipping on $(uname -s)"
	exit 0
fi
sudo apt-get update -qq
sudo apt-get install -y -qq time
