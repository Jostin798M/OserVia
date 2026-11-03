from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Permite iniciar sesión con el correo electrónico en lugar del usuario."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get('email', username)
        if not email or password is None:
            return None
        User = get_user_model()
        user = User.objects.filter(email__iexact=email.strip()).order_by('pk').first()
        if user is None:
            User().set_password(password)  # tiempo constante ante usuarios inexistentes
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
