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


class InvalidRoleError(UserHarborError):
    pass


class InvalidPermissionError(UserHarborError):
    pass


class RoleAlreadyExistsError(UserHarborError):
    pass


class PermissionAlreadyExistsError(UserHarborError):
    pass


class UnknownRoleError(UserHarborError):
    pass


class UnknownPermissionError(UserHarborError):
    pass


class PermissionDeniedError(UserHarborError):
    pass
