#!/bin/env bash
set -e

apt update && DEBIAN_FRONTEND=noninteractive apt install -y curl python3 build-essential pkg-config libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm


nvm install 22.3.0
npm install -g yarn
yarn install --ignore-engines
yarn build --dest dist --ignore-engines

# yarn tries to delete its dest folder before building to it, which it can't do to /asset-output
# so we do a little dance to build in a more pliable location then move everything over cleanly
shopt -s dotglob
rm -rf /asset-output/* >/dev/null || echo "No /asset-output files to clean"
mv dist/* /asset-output
