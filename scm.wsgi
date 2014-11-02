import site
site.addsitedir('/var/venvs/scm/lib/python3.4/site-packages')

import sys
sys.path.insert(0, '/var/www/scm')

from main import app as application
