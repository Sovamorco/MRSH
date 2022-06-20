from abc import ABCMeta, abstractmethod
from datetime import datetime
from secrets import token_urlsafe, token_hex

from mail import verification_email
from params import *
from websockets import *


class Method(metaclass=ABCMeta):
    name = None

    @property
    def params(self):
        return []

    @property
    def optional_params(self):
        return []

    @abstractmethod
    def _process(self, **kwargs):
        pass

    def process(self, **kwargs):
        self.check_arguments(kwargs)
        return self._process(**kwargs)

    def check_arguments(self, params):
        for param in self.params:
            if param.name not in params:
                raise MissingRequiredArgument(param.name)
            params[param.name] = param.validate(params[param.name])
        for param in self.optional_params:
            if param.name in params:
                params[param.name] = param.validate(params[param.name])


class RegisterUser_0_0_1:
    def __init__(self):
        raise DeprecatedVersion


class AuthorizedMethod(Method, metaclass=ABCMeta):
    def __init__(self):
        self.user = None

    @property
    def params(self):
        return []

    @abstractmethod
    def _process(self, **kwargs):
        pass

    def process(self, **kwargs):
        try:
            token = kwargs.pop('token')
        except KeyError:
            raise MissingRequiredArgument('token')
        self.user = User.authorize_by_token(token)
        self.check_arguments(kwargs)
        return self._process(**kwargs)


class CreateChat_0_0_1:
    def __init__(self):
        raise DeprecatedVersion


class SendMessage_0_0_1:
    def __init__(self):
        raise DeprecatedVersion


class CreateChat_0_0_2:
    def __init__(self):
        raise DeprecatedVersion


class RegisterUser_0_0_2(Method):
    name = 'register_user'

    @property
    def params(self):
        return [Name('first_name', True, 36), Name('last_name', True, 36), String('email', True), String('password', True)]

    @staticmethod
    def user_exists(email):
        if sql_req('SELECT id FROM `users` WHERE email=%s', email, fetch_one=True) or \
                sql_req('SELECT id FROM `unverified_users` WHERE email=%s', email, fetch_one=True):
            raise EmailAlreadyRegistered

    @staticmethod
    def send_registration_email(email):
        vercode = token_urlsafe()
        verification_email(email, vercode)
        return vercode

    def _process(self, **kwargs):
        email = kwargs.get('email')
        self.user_exists(email)
        kwargs['verification_code'] = self.send_registration_email(email)
        UnverifiedUser.create(**kwargs)


class VerifyEmail_0_0_2(Method):
    name = 'verify_email'

    @property
    def params(self):
        return [String('code', True)]

    def _process(self, **kwargs):
        user = UnverifiedUser.verify(kwargs.get('code'))
        return {
            'message': 'User successfully verified',
            'user': user
        }


class DenyVerification_0_0_2(Method):
    name = 'deny_verification'

    @property
    def params(self):
        return [String('code', True)]

    def _process(self, **kwargs):
        UnverifiedUser.delete(kwargs.get('code'))
        return {
            'message': 'Verification successfully denied'
        }


class LoginUser_0_0_2(Method):
    name = 'login_user'

    @property
    def params(self):
        return [String('email', True, 0), String('password', True, 0)]

    @staticmethod
    def add_token(user_id):
        selector = token_hex(32)
        validator = token_hex(64)
        hashed = selector + hash_string(validator).decode('utf-8')
        sql_insert('tokens', token=hashed, user_id=user_id)
        return selector + validator

    def _process(self, **kwargs):
        email = kwargs.get('email')
        user = User.authorize(email, kwargs.get('password'))
        res = user.to_dict
        res['token'] = self.add_token(user.id)
        return res


class GetChats_0_0_2(AuthorizedMethod):
    name = 'get_chats'

    def _process(self, **kwargs):
        res = []
        chats = self.user.get_chats()
        for chat in chats:
            lmsg = chat.get_messages(1)
            _chat = {
                **chat.to_dict,
                'last_message': lmsg[0] if lmsg else None,
                'members': chat.get_members()
            }
            res.append(_chat)
        return {
            'results': res
        }


class GetChat_0_0_2(AuthorizedMethod):
    name = 'get_chat'

    @property
    def params(self):
        return [PeerP('peer_id', True, self)]

    @property
    def optional_params(self):
        return [NonNegInt('offset'), NonNegInt('count', 200), Bool('antichronological')]

    def _process(self, **kwargs):
        chat = kwargs.get('peer_id')
        members = chat.get_members()
        messages = chat.get_messages(kwargs.get('count'), kwargs.get('offset'), kwargs.get('antichronological'))
        return {
            'chat': {
                **chat.to_dict,
                'members': members,
            },
            'messages': messages,
        }


class CreateChat_0_0_3(AuthorizedMethod):
    name = 'create_chat'

    @property
    def params(self):
        return [String('title', True, 30)]

    @property
    def optional_params(self):
        return [CSSet('user_ids', UserID('user_ids', True, self)), Bool('private')]

    def _process(self, **kwargs):
        user_ids = {self.user.id} | kwargs.get('user_ids', set())
        private = kwargs.get('private', False)
        if private:
            if len(user_ids) != 2:
                raise CustomBadArgument('{} argument is invalid. Cannot create private chats with more than one user.', 'user_ids')
            if Chat.get_private(user_ids):
                raise ChatAlreadyExists()
        chat = Chat.create(kwargs.get('title'), private)
        chat.send_message(self.user.id, f'{self.user.full_name} created "{chat.title}" {"private" if private else "group"} chat')
        for member in user_ids:
            chat.add_member(member)
        return {
            'chat': {
                **chat.to_dict,
                'members': chat.get_members()
            }
        }


class InviteToChat_0_0_3(AuthorizedMethod):
    name = 'invite_to_chat'

    @property
    def params(self):
        return [PeerP('peer_id', True, self), UserP('user_id', True, self)]

    def _process(self, **kwargs):
        chat = kwargs.get('peer_id')
        target = kwargs.get('user_id')
        if target.id in chat.members:
            raise CustomBadArgument('{} is already a chat member.', target.full_name)
        chat.add_member(target.id)
        chat.send_message(self.user.id, f'{self.user.full_name} invited {target.full_name} to the chat.')


class GetUser_0_0_3(AuthorizedMethod):
    name = 'get_user'

    @property
    def optional_params(self):
        return [UserP('user_id')]

    def _process(self, **kwargs):
        return kwargs.get('user_id') or self.user


class AddFriend_0_0_3(AuthorizedMethod):
    name = 'add_friend'

    @property
    def params(self):
        return [UserID('user_id')]

    def _process(self, **kwargs):
        target_id = kwargs.get('user_id')
        if target_id == self.user.id:
            raise BadArgument('user_id')
        mutual = Friends(self.user.id, target_id).create()
        add_friend(self.user, target_id, mutual)
        return {
            'mutual': mutual
        }


class RemoveFriend_0_0_3(AuthorizedMethod):
    name = 'remove_friend'

    @property
    def params(self):
        return [UserID('user_id', True, self)]

    def _process(self, **kwargs):
        target_id = kwargs.get('user_id')
        if target_id == self.user.id:
            raise BadArgument('user_id')
        was_mutual = Friends(self.user.id, target_id).delete()
        remove_friend(self.user, target_id, was_mutual)
        return {
            'requested': was_mutual
        }


class GetFriends_0_0_3(AuthorizedMethod):
    name = 'get_friends'

    @property
    def optional_params(self):
        return [UserP('user_id')]

    def _process(self, **kwargs):
        target = kwargs.get('user_id') or self.user
        return target.get_friends()


class SendMessage_0_0_3(AuthorizedMethod):
    name = 'send_message'

    @property
    def params(self):
        return [PeerP('peer_id', True, self), String('message', True, 4096)]

    def _process(self, **kwargs):
        chat = kwargs.get('peer_id')
        return {
            'message_id': chat.send_message(self.user.id, kwargs.get('message')).id
        }


class MarkAsRead_0_0_3(AuthorizedMethod):
    name = 'mark_as_read'

    @property
    def params(self):
        return [MessageP('message_id', True, self)]

    def _process(self, **kwargs):
        message = kwargs.get('message_id')
        message.mark_as_read(self.user.id)


class SendMessage_0_0_4(AuthorizedMethod):
    name = 'send_message'

    @property
    def params(self):
        return [PeerP('peer_id', True, self), String('message', True, 4096)]

    def _process(self, **kwargs):
        chat = kwargs.get('peer_id')
        msg = chat.send_message(self.user.id, kwargs.get('message'))
        return {
            'message': msg
        }


class ResendVerification_0_0_4(Method):
    name = 'resend_verification'

    @property
    def params(self):
        return [String('email', True)]

    def _process(self, **kwargs):
        user = UnverifiedUser.get(kwargs.get('email'))
        verification_email(user.email, user.verification_code)


class GetChats_0_0_4(AuthorizedMethod):
    name = 'get_chats'

    def _process(self, **kwargs):
        res = []
        chats = self.user.get_chats()
        for chat in chats:
            lmsg = chat.get_messages(1)
            _chat = {
                **chat.to_dict,
                'last_message': lmsg[0] if lmsg else None,
                'members': chat.get_members()
            }
            res.append(_chat)
        return {
            'results': sorted(res, key=lambda _chat: getattr(_chat.get('last_message'), 'datetime', datetime.min), reverse=True)
        }


class GetChatHistory_0_0_4(AuthorizedMethod):
    name = 'get_chat_history'

    @property
    def params(self):
        return [PeerP('peer_id', True, self)]

    @property
    def optional_params(self):
        return [NonNegInt('offset'), NonNegInt('count', 500), Bool('antichronological')]

    def _process(self, **kwargs):
        chat = kwargs.get('peer_id')
        messages = chat.get_messages(kwargs.get('count'), kwargs.get('offset'), kwargs.get('antichronological'))
        return {
            'chat': chat,
            'messages': messages,
        }


class ChangeProfilePicture_0_0_5(AuthorizedMethod):
    name = 'change_profile_picture'

    @property
    def params(self):
        return [ProfilePicture('file')]

    def _process(self, **kwargs):
        image = kwargs.get('file')
        image_name = token_urlsafe(64) + '.png'
        image.save(PFP_PATH / image_name)
        self.user.update(profile_picture=f'{PFP_URL}/{image_name}')
        return {
            'url': self.user.profile_picture
        }


class SetSettings_0_0_5(AuthorizedMethod):
    name = 'set_settings'

    @property
    def optional_params(self):
        return [Name('first_name', True, 36), Name('last_name', True, 36), ScreenName('screen_name')]

    @property
    def updateable(self):
        return [param.name for param in self.optional_params]

    def _process(self, **kwargs):
        filtered = {k: v for k, v in kwargs.items() if k in self.updateable}
        self.user.update(**filtered)
        return {
            'updated': filtered
        }


class ChangeChatImage_0_0_5(AuthorizedMethod):
    name = 'change_chat_image'

    @property
    def params(self):
        return [PeerP('peer_id', True, self), ProfilePicture('file')]

    def _process(self, **kwargs):
        image = kwargs.get('file')
        chat = kwargs.get('peer_id')
        image_name = token_urlsafe(64) + '.png'
        image.save(CHAT_IMAGE_PATH / image_name)
        chat.update(image=f'{CHAT_IMAGE_URL}/{image_name}')
        return {
            'url': chat.image
        }


class GetChat_0_0_5(AuthorizedMethod):
    name = 'get_chat'

    @property
    def optional_params(self):
        return [PeerP('peer_id', True, self), UserP('user_id'), NonNegInt('offset'), NonNegInt('count', 200), Bool('antichronological')]

    def _process(self, **kwargs):
        chat = kwargs.get('peer_id')
        user = kwargs.get('user_id')
        if not chat and not user:
            raise MissingRequiredArgument('peer_id or user_id should be present.')
        if not chat:
            if user.id == self.user.id:
                raise BadArgument('user_id')
            chat = Chat.get_private({self.user.id, user.id})
        messages = chat.get_messages(kwargs.get('count'), kwargs.get('offset'), kwargs.get('antichronological'))
        return {
            'chat': {
                **chat.to_dict,
                'members': chat.get_members(),
                'user_last_read': chat.get_user_last_read(self.user.id),
            },
            'messages': messages,
        }


class GetChats_0_0_5(AuthorizedMethod):
    name = 'get_chats'

    def _process(self, **kwargs):
        res = []
        chats = self.user.get_chats()
        for chat in chats:
            lmsg = chat.get_messages(1)
            _chat = {
                **chat.to_dict,
                'last_message': lmsg[0] if lmsg else None,
                'members': chat.get_members(),
                'user_last_read': chat.get_user_last_read(self.user.id),
            }
            res.append(_chat)
        return {
            'results': sorted(res, key=lambda _chat: getattr(_chat.get('last_message'), 'datetime', datetime.min), reverse=True)
        }


class GetChatHistory_0_0_5(AuthorizedMethod):
    name = 'get_chat_history'

    @property
    def params(self):
        return [PeerP('peer_id', True, self)]

    @property
    def optional_params(self):
        return [NonNegInt('offset'), NonNegInt('count', 500), Bool('antichronological')]

    def _process(self, **kwargs):
        chat = kwargs.get('peer_id')
        messages = chat.get_messages(kwargs.get('count'), kwargs.get('offset'), kwargs.get('antichronological'))
        return {
            'chat': {
                **chat.to_dict,
                'user_last_read': chat.get_user_last_read(self.user.id),
            },
            'messages': messages,
        }
