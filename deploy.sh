#!/bin/sh

HOST="$1"

rsync -rv --exclude=scm.config --exclude=.git --exclude=.gitignore --exclude=examples --exclude=__pycache__ --exclude=scm.db --exclude=scm.wsgi --exclude=*.pyc --exclude=".*" --exclude=test ./ "$HOST":/var/www/scm
