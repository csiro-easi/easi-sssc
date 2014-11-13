#!/bin/sh

HOST="$1"

# Copy the files to the server
rsync -rv --exclude=scm.config --exclude=.git --exclude=.gitignore --exclude=examples --exclude=__pycache__ --exclude=scm.db --exclude=scm.wsgi --exclude=*.pyc --exclude=".*" --exclude=test ./ "$HOST":/var/www/scm

# Log into the server and restart apache
ssh -t "$HOST" sudo apache2ctl graceful
# ssh -t "$HOST" bash -c 'sudo apache2ctl graceful && sudo tail -f /var/log/apache2/error.log'
