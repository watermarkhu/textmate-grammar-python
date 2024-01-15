#!/bin/bash
# install essential packages

if [ ! -d "/node_root" ]; then
    mkdir node_root
fi

if [ ! -f "node_root/index.js" ]; then
    cp ./index.js node_root/
fi

cd node_root

if [ ! -d "node_modules/oniguruma" ] ||
    [ ! -d "node_modules/typescript" ] ||
    [ ! -d "node_modules/vscode-oniguruma" ] ||
    [ ! -d "node_modules/vscode-textmate" ]; then

    if ! command -v npm &>/dev/null; then

        sudo apt update
        sudo apt install -y curl vim wget git python3 build-essential

        # install nvm
        if ! command -v nvm &>/dev/null; then
            wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
        fi
        export NVM_DIR="$HOME/.nvm"
        source "$NVM_DIR/nvm.sh"

        nvm install --lts
    fi

    npm init -y
    npm install oniguruma typescript vscode-oniguruma vscode-textmate
fi
