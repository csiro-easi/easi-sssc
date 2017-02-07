# coding: utf-8

from models import db, Problem, Solution, Toolbox, Dependency, ToolboxDependency, SolutionDependency, create_database, drop_tables, index_entry
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

def solution_dep(solution, **args):
    """Create and return a link between solution and a Dependency specified by args.

    If a Dependency exists in the database that matches args, it will be used.
    Otherwise a new Dependency will be created in the database, and linked to
    solution.

    See models.Dependency for a description of valid args.

    """
    return SolutionDependency.create(
        solution=solution,
        dependency=Dependency.get_or_create(**args)[0]
    )

def toolbox_dep(toolbox, **args):
    """Create and return a link between toolbox and a Dependency specified by args.

    If a Dependency exists in the database that matches args, it will be used.
    Otherwise a new Dependency will be created in the database, and linked to
    toolbox.

    See models.Dependency for a description of valid args.

    """
    return ToolboxDependency.create(
        toolbox=toolbox,
        dependency=Dependency.get_or_create(**args)[0]
    )
