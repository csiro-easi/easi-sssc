# Import app into the global namespace
from .app import app

# Make sure we initialise the views for the main and admin sites
import sssc.admin
import sssc.views

# Include scripts for the flask/click command line.
import sssc.cli
