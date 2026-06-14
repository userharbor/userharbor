class UserHarborError(Exception):
    pass


class InvalidUsernameError(UserHarborError):
    pass


class InvalidEmailError(UserHarborError):
    pass


class WeakPasswordError(UserHarborError):
    pass


class InvalidVerificationCodeError(UserHarborError):
    pass


class InvalidPasswordError(UserHarborError):
    pass


class UnverifiedUserError(UserHarborError):
    pass


class InvalidSessionTokenError(UserHarborError):
    pass
