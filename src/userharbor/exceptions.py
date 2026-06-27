class UserHarborError(Exception):
    pass


class InvalidUsernameError(UserHarborError):
    pass


class InvalidEmailError(UserHarborError):
    pass


class WeakPasswordError(UserHarborError):
    pass


class InvalidVerificationTokenError(UserHarborError):
    pass


class InvalidCredentialsError(UserHarborError):
    pass


class UnverifiedUserError(UserHarborError):
    pass


class InvalidSessionTokenError(UserHarborError):
    pass


class InvalidPasswordResetTokenError(UserHarborError):
    pass
