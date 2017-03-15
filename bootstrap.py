# coding: utf-8

from models import db, Problem, Solution, Toolbox, Dependency, \
    ToolboxDependency, SolutionDependency, create_database, drop_tables, \
    index_entry
from security import user_datastore

BOOTSTRAP_USER = dict(email='geoffrey.squire@csiro.au',
                      password='password',
                      name='Geoff Squire')


def bootstrap():
    db.connect()
    drop_tables(db)

    create_database(db)

    # Create a sample user and bootstrap entries
    user = user_datastore.create_user(**BOOTSTRAP_USER)
    import entries.escript
    entries.escript.create(user)

    # close the connection in case this is called from outside the main app,
    # and return the created user identification.
    db.close()
    return dict([(k, BOOTSTRAP_USER[k]) for k in ['email']])


def create_entry(cls, **kwargs):
    """Create catalogue entry and add it to the text index, then return it.

    """
    entry = cls.create(**kwargs)
    index_entry(entry)
    return entry


def create_problem(**kwargs):
    return create_entry(Problem, **kwargs)


def create_toolbox(**kwargs):
    return create_entry(Toolbox, **kwargs)


def create_solution(**kwargs):
    return create_entry(Solution, **kwargs)
