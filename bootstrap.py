# coding: utf-8

from models import db, Problem, Solution, Toolbox,  drop_tables,  index_entry
from security import user_datastore, user_role, admin_role, initialise_db


def bootstrap():
    db.connect()
    drop_tables(db)
    initialise_db()

    # import entries.escript
    # entries.escript.create(user1)

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
