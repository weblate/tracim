#!/bin/bash

. bash_library.sh # source bash_library.sh

windoz=""
if  [[ $1 = "-w" ]]; then
    windoz="windoz"
fi

echo -e "\n${BROWN}/!\ ${NC}this script does not run 'npm install'\n${BROWN}/!\ ${NC}it also assumes your webpack dev server of frontend is running"

log "cd frontend_lib"
cd frontend_lib
log "npm run buildtracimlib$windoz"
npm run buildtracimlib$windoz
cd -

log "cd frontend_app_html-document"
cd frontend_app_html-document
log "npm run build$windoz # for frontend_app_html-document"
npm run build$windoz
log "cp dist/html-document.app.js"
cp dist/html-document.app.js ../frontend/dist/app
