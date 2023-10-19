#!/bin/bash
# install essential packages
apt update
apt install -y curl vim wget git python3 build-essential

# install nvm
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
export NVM_DIR="$HOME/.nvm"
source "$NVM_DIR/nvm.sh" 

# create the environment
mkdir /node_root
cd /node_root

# install the necessary packages 
nvm install --lts
npm init -y
npm install oniguruma typescript vscode-oniguruma vscode-textmate
