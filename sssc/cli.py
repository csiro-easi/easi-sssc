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
