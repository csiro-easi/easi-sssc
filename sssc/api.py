"""Functions for defining and retrieving API objects. """


def expose(name=None, sense=None):
    """Wrap a member function/property to be exposed through the api.

    The wrapped function (or getter function for a property) will have a new
    '_api' attribute added with a tuple value (object_name, api_name), where
    object_name is the name of the wrapped object to look up and api_name is
    the name to expose it under in the api.

    :param name:
        If not None, use this as the name for the field in the api.

    :param sense:
        An optional string value to be associated with the api annotation.

    """
    def wrapper(f):
        wrapped = f

        # If f is a property object, attach the api annotation to the getter
        # function, since we can't add attributes to a property.
        if isinstance(f, property):
            f = f.fget

        # Use the name of the function by default
        api_name = f.__name__ if name is None else name

        # Attach the api info to the _api attribute and return the wrapped
        # object.
        f._api_name = api_name
        f._api_sense = sense
        return wrapped
    return wrapper


def get_exposed(x, handler=None, **kwargs):
    """Return a dict of exposed attributes and their values from x.

    If an exposed field has an _api_sense attribute, it will be used to look up
    a handler function named <_api_sense>_handler in kwargs. If such a function
    is provided, the exposed value will be the result of invoking that function
    on the attribute value. If handler is supplied, it will be invoked for
    every value that does not have another supplied handler.

    """
    exposed = {}

    # Find attributes of x that have been annotated with our _api attribute.
    for xname in dir(type(x)):
        a = getattr(type(x), xname)

        # If it's a property object, look at the getter fn for the annotation
        if isinstance(a, property):
            a = a.fget

        apiname = getattr(a, '_api_name', None)
        if apiname:
            value = getattr(x, xname)
            sense = getattr(a, '_api_sense', None)
            if sense:
                handler = kwargs.get('{}_handler'.format(sense))
            else:
                handler = kwargs.get('handler')
            if callable(handler):
                value = handler(value)
            exposed[apiname] = value

    return exposed


