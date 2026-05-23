from functools import wraps

from django.core.exceptions import PermissionDenied


def role_required(allowed_roles):
    """Validate user role via Django groups."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied

            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_roles = set(user.groups.values_list('name', flat=True))
            if any(role in user_roles for role in allowed_roles):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied

        return wrapper

    return decorator
