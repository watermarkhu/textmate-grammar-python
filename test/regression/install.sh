#!/bin/bash
# install essential packages
apt update
apt install -y curl vim wget git python3 build-essential

# install nvm
if ! command -v nvm &> /dev/null
then
    wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
fi
export NVM_DIR="$HOME/.nvm"
source "$NVM_DIR/nvm.sh"

# create the environment
if [ ! -d "/node_root" ]
then
    mkdir node_root
fi
cp ./index.js node_root/
cd node_root

# install the necessary packages 
if ! command -v npm &> /dev/null
then
    nvm install --lts
    npm init -y
fi
npm install oniguruma typescript vscode-oniguruma vscode-textmate
