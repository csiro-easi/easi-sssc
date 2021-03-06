import argparse

from . import app
from .bootstrap import bootstrap


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manage the SSC app")
    parser.add_argument('-b', '--bootstrap', action='store_true',
                        help="Initialise a new database")
    args = parser.parse_args()

    if args.bootstrap:
        bootstrap()

    # Run the server
    app.run(debug=True, host="0.0.0.0", threaded=True)
