# Regression testing against vscode-textmate

Running the regression test requires installing npm and node and the following dependencies:
- typescript 
- vscode-textmate
- vscode-oniguruma 
- oniguruma 

The node root should be initialized in a subfolder `node_root`. The `index.js` should thereafter
be copied into this `node_root` folder. The `install.sh` shows the required steps to setup the environment. 

```
.
|--  node_root
|   |-- node_modules
|   |-- syntax
|   |-- index.js
|   |-- package.json
|-- .gitignore
|-- index.js
|-- install.sh
|-- readme.md
|-- test.regression.py
```