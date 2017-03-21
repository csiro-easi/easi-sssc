# coding: utf-8

from models import db, Problem, Solution, Toolbox,  drop_tables,  index_entry
from security import user_datastore, user_role, admin_role, initialise_db


def bootstrap():
    db.connect()
    drop_tables(db)
    initialise_db()

    # Create a sample user and bootstrap entries
    user1 = user_datastore.create_user(email='geoffrey.squire@csiro.au',
                                       password='password',
                                       name='Geoff Squire')
    user_datastore.add_role_to_user(user1, admin_role)
    user_datastore.add_role_to_user(user1, user_role)

    user = user_datastore.create_user(email='josh.vote@csiro.au',
                                      password='password',
                                      name='Josh Vote')
    user_datastore.add_role_to_user(user, user_role)

    import entries.escript
    entries.escript.create(user1)

    # close the connection in case this is called from outside the main app
    db.close()


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
