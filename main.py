import click
from app import app
import admin
from bootstrap import bootstrap
import views
import argparse


@app.cli.command()
def initdb():
    """Initialise the database."""
    click.echo('Initialising the database.')
    bootstrap()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manage the SSC app")
    parser.add_argument('-b', '--bootstrap', action='store_true',
                        help="Initialise a new database")
    args = parser.parse_args()

    if args.bootstrap:
        from bootstrap import bootstrap
        bootstrap()

    # Run the server
    app.run(debug=True, host="0.0.0.0", threaded=True)
