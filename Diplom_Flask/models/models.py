from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, username, is_superuser):
        self.id = id
        self.username = username
        self.is_superuser = is_superuser
