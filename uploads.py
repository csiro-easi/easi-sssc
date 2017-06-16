from pathlib import PurePath, Path
from werkzeug.utils import secure_filename

from app import app
import models


def allowed_file(filename):
    """Return True if filename is allowed as an attachment."""
    suffix = PurePath(filename).suffix
    if not suffix:
        # Can't disallow based on extension
        return True
    allowed = set(app.config.get('UPLOADED_ATTACHMENTS_ALLOW', []))
    denied = set(app.config.get('UPLOADED_ATTACHMENTS_DENY', []))
    return suffix in allowed or suffix not in denied


def save_attachment(entry, file, user, name=None):
    """Save file as an attachment for entry, return the attachment model.

    Uses the basename of the file as the default name for the attachment,
    unless name is passed.

    """
    if not name:
        name = PurePath(file.filename).name

    # Make sure we have a safe filename
    filename = Path(secure_filename(file.filename))

    # Create the upload object with the default filename first, so we can use
    # the id to ensure the final filename is unique.
    attachment = models.UploadedResource.create(filename=filename,
                                                name=name,
                                                user=user.id)

    # Append the resource id to the filename to ensure it is unique before
    # saving the file.
    filename = filename.with_name(filename.name + '.' + str(attachment.id))
    attachment.filename = filename
    attachment.save()
    file.save(str(app.config['UPLOADS_DEFAULT_DEST'] / filename))

    # Store the association with entry.
    rel_class_name = '{}Attachment'.format(models.entry_type(entry))
    rel_class = getattr(models, rel_class_name)
    rel = rel_class.create(attachment=attachment, entry=entry)
    return rel
