from app import app
from flask.ext.admin import Admin
from flask.ext.admin.contrib.peewee import ModelView
from models import User, Entry, Problem, Solution, Toolbox

admin = Admin(app)


# Add admin views here
class UserAdmin(ModelView):
    pass


class EntryAdmin(ModelView):
    inline_models = (Problem, Toolbox, Solution)


admin.add_view(UserAdmin(User))
admin.add_view(EntryAdmin(Entry))
