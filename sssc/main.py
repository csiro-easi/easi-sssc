import argparse
import click

from . import app
from .bootstrap import bootstrap
from .models import db, update_index


@app.cli.command()
def initdb():
    """Initialise the database."""
    click.echo('Initialising the database.')
    bootstrap()


@app.cli.command()
def index():
    """Reinitialise the text index."""
    click.echo("Re-initialising the text index.")
    db.connect()
    update_index()
    db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manage the SSC app")
    parser.add_argument('-b', '--bootstrap', action='store_true',
                        help="Initialise a new database")
    args = parser.parse_args()

    if args.bootstrap:
        bootstrap()

    # Run the server
    app.run(debug=True, host="0.0.0.0", threaded=True)
