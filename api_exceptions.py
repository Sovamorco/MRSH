from constants import *


class InvalidRequest(Exception):
    code = 0
    string = 'invalid_request'
    message = 'Invalid request.'


class InvalidVersion(InvalidRequest):
    code = 1
    string = 'invalid_version'
    message = f'Invalid version. Current latest version is {LATEST_VERSION}.'


class InvalidMethod(InvalidRequest):
    code = 2
    string = 'invalid_method'
    message = 'No such method found for specified version or any of the older ones.'


class ArgumentsError(InvalidRequest):
    code = 3
    string = 'invalid_arguments'
    message = 'Invalid arguments.'


class CustomBadArgument(ArgumentsError):
    code = 4
    string = 'invalid_argument'

    def __init__(self, message, arg):
        self._message = message
        self.arg = arg

    @property
    def message(self):
        return self._message.format(self.arg)


class BadArgument(CustomBadArgument):
    def __init__(self, arg):
        super().__init__('Invalid argument: {}', arg)


class MissingRequiredArgument(CustomBadArgument):
    code = 5
    string = 'missing_argument'

    def __init__(self, arg):
        super().__init__('Missing required argument: {}', arg)


class BadArgumentType(CustomBadArgument):
    code = 6
    string = 'invalid_argument_type'

    def __init__(self, arg):
        super().__init__('Invalid argument type for argument: {}', arg)


class InvalidTokenError(BadArgument):
    code = 7
    string = 'invalid_token'
    message = 'Invalid token.'

    def __init__(self):
        pass


class UserNotFound(CustomBadArgument):
    code = 8
    string = 'user_not_found'

    def __init__(self, arg):
        super().__init__('User with id {} was not found.', arg)


class PeerNotFound(CustomBadArgument):
    code = 9
    string = 'peer_not_found'

    def __init__(self, arg):
        super().__init__('Chat with id {} was not found.', arg)


class DeprecatedVersion(InvalidVersion):
    code = 10
    string = 'deprecated_version'
    message = f'Specified version is deprecated. Current latest version is {LATEST_VERSION}.'


class EmailAlreadyRegistered(ArgumentsError):
    code = 11
    string = 'email_already_registered'
    message = 'This email is already registered.'


class EmailNotVerified(InvalidRequest):
    code = 12
    string = 'email_not_verified'
    message = 'This email is not verified. Please follow the link sent in email.'


class UserDoesNotExist(ArgumentsError):
    code = 13
    string = 'user_does_not_exist'
    message = 'User with such email address does not exist.'


class WrongPassword(ArgumentsError):
    code = 14
    string = 'wrong_password'
    message = 'Invalid password.'


class VerificationError(ArgumentsError):
    code = 15
    string = 'verification_error'
    message = 'Verification error.'


class AlreadyVerified(VerificationError):
    code = 16
    string = 'already_verified'
    message = 'Email already verified.'


class AlreadyFriends(ArgumentsError):
    code = 17
    string = 'already_friends'
    message = 'You are already friends with target user.'


class NotFriends(ArgumentsError):
    code = 18
    string = 'not_friends'
    message = 'You are not friends with target user.'


class MessageNotFound(CustomBadArgument):
    code = 19
    string = 'message_not_found'

    def __init__(self, arg):
        super().__init__('Message with id {} was not found.', arg)


class BadEmail(CustomBadArgument):
    code = 20
    string = 'invalid_email'

    def __init__(self, arg):
        super().__init__('Invalid email: "{}".', arg)


class BadImage(BadArgument):
    code = 21
    string = 'invalid_image'
    message = 'Unidentified image format.'

    def __init__(self):
        pass


class ScreenNameAlreadyTaken(BadArgument):
    code = 22
    string = 'screen_name_taken'
    message = 'This screen name is already taken.'

    def __init__(self):
        pass


class ChatAlreadyExists(BadArgument):
    code = 23
    string = 'chat_exists'
    message = 'Private chat with specified users already exists.'

    def __init__(self):
        pass
