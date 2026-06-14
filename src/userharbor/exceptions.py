class UserHarborError(Exception):
    pass


class InvalidUsernameError(UserHarborError):
    pass


class InvalidEmailError(UserHarborError):
    pass


class WeakPasswordError(UserHarborError):
    pass
