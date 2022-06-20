from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

from objects import *


class Param:
    def __init__(self, _type, name, has_to_be_truthy=False):
        self.type = _type
        self.name = name
        self.truthy = has_to_be_truthy

    @property
    def custom_checks(self):
        return []

    def validate(self, value):
        if not isinstance(value, self.type):
            try:
                value = self.type(value)
            except ValueError:
                raise BadArgumentType(self.name)
        elif self.truthy and not value:
            raise BadArgument(self.name)
        for check in self.custom_checks:
            res = check(value)
            if res:
                value = res
        return value


class String(Param):
    def __init__(self, name, has_to_be_truthy=False, max_length=0):
        self.max_length = max_length
        super().__init__(str, name, has_to_be_truthy)

    def length_check(self, value):
        if self.max_length and len(value) > self.max_length:
            raise CustomBadArgument(f'Invalid argument: {{}}. Argument length exceeds {self.max_length}.', self.name)

    @staticmethod
    def strip_check(value):
        return value.strip()

    @property
    def custom_checks(self):
        return [self.length_check, self.strip_check]


class Name(String):
    @staticmethod
    def capitalize_check(value):
        return value.capitalize()

    def numbers_check(self, value):
        if any(char.isdigit() for char in value):
            raise BadArgument(self.name)

    @property
    def custom_checks(self):
        return super().custom_checks + [self.capitalize_check, self.numbers_check]


class NonNegInt(Param):
    def __init__(self, name, max_value=0, has_to_be_truthy=False):
        self.max_value = max_value
        super().__init__(int, name, has_to_be_truthy)

    def negativity_check(self, value):
        if value < 0:
            raise BadArgument(self.name)

    def max_check(self, value):
        if self.max_value and value > self.max_value:
            raise BadArgument(self.name)

    @property
    def custom_checks(self):
        return [self.negativity_check, self.max_check]


class Bool(Param):
    def __init__(self, name):
        super().__init__(bool, name, False)

    def validate(self, value):
        if not value or str(value) in ['false', 'False', '0', '']:
            return False
        return True


class UserID(Param):
    def __init__(self, name, friend=False, method=None):
        self.friend = friend
        self.method = method
        super().__init__(str, name, True)

    @staticmethod
    def lower_check(value):
        return value.lower()

    @staticmethod
    def resolve_user(value):
        if value.isdigit():
            return User.get(user_id=value)
        if value.startswith('user') and value[4:].isdigit():
            return User.get(user_id=value[4:])
        return User.get(screen_name=value)

    def user_check(self, value):
        return self.resolve_user(value).id

    def friend_check(self, value):
        if not self.friend or self.method.user.id == value:
            return
        fr = Friends(self.method.user.id, value)
        if not (fr.exists and fr.mutual):
            raise NotFriends

    @property
    def custom_checks(self):
        return [self.lower_check, self.user_check, self.friend_check]


class UserP(UserID):
    def user_check(self, value):
        return self.resolve_user(value)

    def friend_check(self, value):
        super().friend_check(value.id)


class PeerID(Param):
    def __init__(self, name, assess=False, method=None):
        self.assess = assess
        self.method = method
        super().__init__(int, name, True)

    def peer_check(self, value):
        chat = Chat.get(value)
        if self.assess:
            chat.assess_access(self.method.user.id)

    @property
    def custom_checks(self):
        return [self.peer_check]


class PeerP(PeerID):
    def peer_check(self, value):
        chat = Chat.get(value)
        if self.assess:
            chat.assess_access(self.method.user.id)
        return chat


class MessageID(Param):
    def __init__(self, name, assess=False, method=None):
        self.assess = assess
        self.method = method
        super().__init__(int, name, True)

    def message_check(self, value):
        message = Message.get(value)
        if self.assess:
            message.assess_access(self.method.user.id)

    @property
    def custom_checks(self):
        return [self.message_check]


class MessageP(MessageID):
    def message_check(self, value):
        message = Message.get(value)
        if self.assess:
            message.assess_access(self.method.user.id)
        return message


class ProfilePicture(Param):
    def __init__(self, name):
        super().__init__(FileStorage, name, True)

    @staticmethod
    def image_check(value):
        try:
            return Image.open(value)
        except (UnidentifiedImageError, AttributeError):
            raise BadImage

    @staticmethod
    def create_pfp(image):
        image_width, image_height = image.size
        side = min(image_width, image_height)
        resized = image.resize((1024, 1024),
                               box=((image_width - side) // 2, (image_height - side) // 2, (image_width + side) // 2, (image_height + side) // 2))
        if resized.mode != 'RGBA':
            return resized
        bg = Image.new('RGBA', resized.size, 'WHITE')
        bg.paste(resized, None, resized)
        return bg

    @property
    def custom_checks(self):
        return [self.image_check, self.create_pfp]


class ScreenName(String):
    def __init__(self, name):
        super().__init__(name, True, 20)

    def numbers_check(self, value):
        if all(char.isdigit() for char in value):
            raise BadArgument(self.name)

    @staticmethod
    def lower_check(value):
        return value.lower()

    def user_check(self, value):
        if value.startswith('user') and value[4:].isdigit():
            raise BadArgument(self.name)

    @staticmethod
    def unique_check(value):
        try:
            User.get(screen_name=value)
            raise ScreenNameAlreadyTaken
        except UserNotFound:
            pass

    @property
    def custom_checks(self):
        return super().custom_checks + [self.numbers_check, self.lower_check, self.user_check, self.unique_check]


class CSSet:
    def __init__(self, name, param):
        self.name = name
        self.param = param

    def validate(self, value):
        if not isinstance(value, str):
            try:
                value = str(value)
            except ValueError:
                raise BadArgumentType(self.name)
        res = set()
        for part in value.split(','):
            part = part.strip()
            if part:
                res.add(self.param.validate(part))
        return res
