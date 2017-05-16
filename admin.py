from flask import abort, flash, redirect, request, url_for
from flask_admin import Admin, helpers as admin_helpers, expose
from flask_admin.actions import action
from flask_admin.babel import gettext, ngettext
from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.form import CustomModelConverter
from flask_admin.form import BaseForm
from flask_security import current_user
import requests
from wtforms import fields
from app import app
from security import security, is_admin, is_user
from models import Problem, Solution, Toolbox, User, UserRoles, \
    SolutionDependency, ToolboxDependency, \
    SolutionImage, ToolboxImage, \
    SolutionVar, ToolboxVar, JsonField, Entry, \
    ProblemTag, ToolboxTag, SolutionTag
from signatures import hash_entry
from views import model_url

admin = Admin(app, template_mode='bootstrap3')


# Fields that do not cause a version change when they are changed.
_ignored_dirty_fields = frozenset({
    'published'
})


class VarValuesConverter(CustomModelConverter):
    def __init__(self, view, additional=None):
        super().__init__(view, additional)
        self.converters[JsonField] = self.handle_json

    def handle_json(self, model, field, **kwargs):
        return field.name, fields.TextField(**kwargs)


class ProtectedModelView(ModelView):
    """Limit access the admin views.

    Require user to be authenticated to access these views at all.

    Restrict the entries available for admin by a regular user to their own,
    while allowing admin users to administer everything.

    """
    # Restrict access generally to active and authenticated users
    def is_accessible(self):
        return (current_user.is_active and
                current_user.is_authenticated and
                is_user())

    def _handle_view(self, name, **kwargs):
        """Override to redirect users when a view is not accessible."""
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class UserRolesForm(BaseForm):
    def validate(self):
        if not super().validate():
            return False
        seen = set()
        for userrole in self.data['roles']:
            role = userrole['role']
            if role in seen:
                self['roles'].errors.append('Please select distinct roles.')
                return False
            else:
                seen.add(role)
        return True


# Add admin views here
class UserAdmin(ProtectedModelView):
    column_exclude_list = ['password']
    form_base_class = UserRolesForm
    form_excluded_columns = ['id', 'confirmed_at', 'password']
    inline_models = [(UserRoles, dict(form_label='Roles'))]

    # Only allow admins to access the User admin views
    def is_accessible(self):
        return is_admin()


def is_version_bump_required(model):
    """Return True if the pending changes to model require a version bump.

    This relies on checking the dirty fields of model, so must be called before
    the changes are saved.

    """
    return not model._dirty.issubset(_ignored_dirty_fields)


class EntryModelView(ProtectedModelView):
    """View for administering all Entries.

    Control access to entries based on user authorisation.

    Handles versioning of entries as they are created and modified.

    TODO: Decide on whether/how to limit deletion

    """
    can_view_details = True
    column_editable_list = ['name', 'description']
    column_filters = ['name', 'published', 'created_at']
    column_list = ['name', 'description', 'author', 'version', 'created_at', 'published']
    column_sortable_list = ['author', 'published', 'created_at']
    create_modal = True
    details_modal = False
    edit_modal = True
    form_excluded_columns = ['author',
                             'latest',
                             'version',
                             'created_at',
                             'entry_hash',
                             'published']

    # If user does not have the 'admin' role, only allow them to administer
    # their own views.
    def get_query(self):
        # Start with the default query
        query = super().get_query()

        # Limit results to those owned by a regular users.
        if not is_admin():
            query = query.where(self.model.author == current_user.id)

        # Do not allow changing history - hide old versions of entries.
        query = query.where(self.model.latest == self.model.id)

        return query

    def get_one(self, id):
        # Default is to try to retrieve entry with id.
        it = super().get_one(id)

        # If we found the entry, throw not authorized if it's not for the
        # current user and they're not at admin
        if not is_admin() and (it.author.id != current_user.id):
            abort(403)

        return it

    def on_model_change(self, form, model, is_created=False):
        """Maintain model metadata."""

        # Update model metadata, unless it's just changing the published
        # status.
        if is_version_bump_required(model):
            model.update_metadata(is_created)

        # Check external resources
        checks = model.check_resources()
        if not checks.succeeded():
            for check in checks.get_errors():
                for e in check['errors']:
                    flash('{}: {}'.format(type(e), e))

    def after_model_change(self, form, model, is_created=False):
        """Update 'latest' links and entry hashes once we have an id."""
        model.latest = model.id
        model.save()
        # Hash updated content and store result with model
        if isinstance(model, Entry):
            entry_json = requests.get(model_url(model)).text
            model.entry_hash = hash_entry(
                entry_json,
                hash_alg=app.config['ENTRY_HASH_FUNCTION']
            )
        model.save()

    @action("publish", "Publish",
            "Are you sure you want to publish the selected entries?")
    def action_publish(self, ids):
        try:
            query = self.model.select().where(self.model.id.in_(ids))

            count = 0
            for instance in query:
                if not instance.published:
                    instance.published = True
                    instance.save()
                    count += 1

            flash(ngettext('Entry was successfully published.',
                           '%(count)s entries were successfully published.',
                           count,
                           count=count))
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(
                gettext('Failed to publish entries. %(error)s', error=str(ex)),
                'error'
            )

    @action("unpublish", "Unpublish",
            "Are you sure you want to unpublish the selected entries?")
    def action_unpublish(self, ids):
        try:
            query = self.model.select().where(self.model.id.in_(ids))

            count = 0
            for instance in query:
                if instance.published:
                    instance.published = False
                    instance.save()
                    count += 1

            flash(ngettext('Entry was successfully unpublished.',
                           '%(count)s entries were successfully unpublished.',
                           count,
                           count=count))
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash(
                gettext('Failed to unpublish entries. %(error)s', error=str(ex)),
                'error'
            )


class ProblemAdmin(EntryModelView):
    inline_models = (ProblemTag,)


class SolutionAdmin(EntryModelView):
    form_excluded_columns = EntryModelView.form_excluded_columns + \
                            ['template_hash']
    model_form_converter = VarValuesConverter
    inline_models = (
        SolutionDependency,
        SolutionImage,
        SolutionVar,
        SolutionTag
    )


class ToolboxAdmin(EntryModelView):
    form_excluded_columns = EntryModelView.form_excluded_columns + \
                            ['puppet_hash']
    model_form_converter = VarValuesConverter
    inline_models = (
        ToolboxDependency,
        ToolboxImage,
        ToolboxVar,
        ToolboxTag
    )


admin.add_view(UserAdmin(User))
# admin.add_view(UserProfile(User, endpoint='profile'))
admin.add_view(ProblemAdmin(Problem))
admin.add_view(SolutionAdmin(Solution))
admin.add_view(ToolboxAdmin(Toolbox))


# Integrate flask-admin and flask-security
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )
