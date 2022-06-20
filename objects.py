from api_exceptions import *
from crypto import *
from sql_utils import *


class User:
    def __init__(self, payload):
        self.id = payload.get('id')
        self.first_name = payload.get('first_name')
        self.last_name = payload.get('last_name')
        self.profile_picture = payload.get('profile_picture')
        self.screen_name = payload.get('screen_name') or f'user{self.id}'
        self.email = payload.get('email')
        self.password = payload.get('password')

    @classmethod
    def get(cls, user_id=None, screen_name=None):
        res = sql_req('SELECT * FROM `users` WHERE ' + ('id=%s' if user_id else 'screen_name=%s'), user_id or screen_name, fetch_one=True)
        if not res:
            raise UserNotFound(user_id or screen_name)
        return cls(res)

    @classmethod
    def authorize(cls, email, password):
        res = sql_req('SELECT * FROM `users` WHERE email=%s', email, fetch_one=True)
        if not res:
            UnverifiedUser.get(email)
            raise EmailNotVerified
        if not verify_hashed_string(password, res.get('password')):
            raise WrongPassword
        return cls(res)

    @classmethod
    def authorize_by_token(cls, token):
        selector, validator = token[:64], token[64:]
        res = sql_req('SELECT user_id, token FROM `tokens` WHERE SUBSTR(token, 1, 64)=%s', selector, fetch_one=True)
        if not res or not verify_hashed_string(validator, res.get('token')[64:]):
            raise InvalidTokenError
        return cls.get(res.get('user_id'))

    @property
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'profile_picture': self.profile_picture,
            'screen_name': self.screen_name,
        }

    def get_friends(self):
        sent = [el["target"] for el in sql_req('SELECT target FROM `friends` WHERE sender=%s', self.id, fetch_all=True)]
        received = [el["sender"] for el in sql_req('SELECT sender FROM `friends` WHERE target=%s', self.id, fetch_all=True)]
        res = {
            'mutual': [],
            'incoming': [],
            'outgoing': []
        }
        for friend in set(sent + received):
            if friend in sent and friend in received:
                res['mutual'].append(User.get(friend))
            elif friend in sent:
                res['outgoing'].append(User.get(friend))
            else:
                res['incoming'].append(User.get(friend))
        return res

    def get_chats(self):
        chats = sql_req('SELECT chats.* FROM chats '
                        'INNER JOIN members ON members.chat_id = chats.id '
                        'WHERE members.member_id = %s', self.id, fetch_all=True)
        return [Chat(chat) for chat in chats]

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def update(self, **kwargs):
        from websockets import change_settings
        updates = ','.join([f'{k}=%s' for k in kwargs])
        sql_req(f'UPDATE `users` SET {updates} WHERE id=%s', *kwargs.values(), self.id)
        vars(self).update(kwargs)
        change_settings(self, kwargs)


class UnverifiedUser(User):
    def __init__(self, payload):
        self.verification_code = payload.pop('verification_code')
        super().__init__(payload)

    # noinspection PyMethodOverriding
    @classmethod
    def get(cls, email):
        res = sql_req('SELECT * FROM `unverified_users` WHERE email=%s', email, fetch_one=True)
        if not res:
            raise UserDoesNotExist
        return cls(res)

    @classmethod
    def create(cls, **kwargs):
        kwargs['password'] = hash_string(kwargs.get('password'))
        sql_insert('unverified_users', **kwargs)

    @classmethod
    def verify(cls, verification_code):
        res = sql_req('SELECT * FROM `unverified_users` WHERE verification_code=%s', verification_code, fetch_one=True)
        if not res:
            raise VerificationError
        return cls(res)._verify()

    def _verify(self):
        sql_req('DELETE FROM `unverified_users` WHERE id=%s', self.id)
        values = vars(self).copy()
        values.pop('id')
        values.pop('verification_code')
        res = sql_insert('users', last_row_id=True, **values)
        return User.get(res)

    @classmethod
    def delete(cls, verification_code):
        res = sql_req('SELECT * FROM `unverified_users` WHERE verification_code=%s', verification_code, fetch_one=True)
        if not res:
            raise VerificationError
        sql_req('DELETE FROM `unverified_users` WHERE id=%s', res.get('id'))


class Friends:
    def __init__(self, sender, target):
        self.sender = sender
        self.target = target

    @property
    def exists(self):
        return bool(sql_req('SELECT id FROM `friends` WHERE sender=%s AND target=%s', self.sender, self.target, fetch_one=True))

    @property
    def mutual(self):
        return Friends(self.target, self.sender).exists

    def create(self):
        if self.exists:
            raise AlreadyFriends
        sql_insert('friends', sender=self.sender, target=self.target)
        return self.mutual

    def delete(self):
        sql_req('DELETE FROM `friends` WHERE sender=%s AND target=%s', self.sender, self.target)
        return self.mutual


class Message:
    def __init__(self, payload):
        self.id = payload.get('id')
        self.chat_id = payload.get('chat_id')
        self.author_id = payload.get('author_id')
        self.text = payload.get('text')
        self.datetime = payload.get('datetime')
        self.author = None

    def get_author(self):
        self.author = User.get(self.author_id)

    @classmethod
    def get(cls, message_id):
        res = sql_req('SELECT id, chat_id, author_id, text, datetime FROM `messages` WHERE id=%s', message_id, fetch_one=True)
        if not res:
            raise MessageNotFound(message_id)
        return cls(res)

    def mark_as_read(self, user_id):
        if self.author_id != user_id:
            sql_req('UPDATE `chats` SET `last_read`=%s WHERE last_read<%s AND id=%s', self.id, self.id, self.chat_id)
            from websockets import read_message
            read_message(self)
        sql_req('UPDATE `members` SET last_read=%s WHERE member_id=%s AND chat_id=%s AND last_read<%s', self.id, user_id, self.chat_id, self.id)

    def assess_access(self, user_id):
        chat = Chat.get(self.chat_id)
        try:
            chat.assess_access(user_id)
        except PeerNotFound:
            raise MessageNotFound(self.id)

    @property
    def to_dict(self):
        if not self.author:
            self.get_author()
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'author_id': self.author_id,
            'text': self.text,
            'datetime': self.datetime,
            'author': self.author,
        }


class Chat:
    def __init__(self, payload):
        self.id = payload.get('id')
        self.title = payload.get('title')
        self.private = payload.get('private')
        self.image = payload.get('image')
        self.last_read = payload.get('last_read')

    @classmethod
    def create(cls, title, private=False):
        res = sql_insert('chats', title=title, private=private, last_row_id=True)
        return cls.get(res)

    @classmethod
    def get(cls, _id):
        res = sql_req('SELECT * FROM `chats` WHERE id=%s', _id, fetch_one=True)
        if not res:
            raise PeerNotFound(_id)
        return cls(res)

    @classmethod
    def get_private(cls, members):
        res = sql_req('SELECT chats.* FROM chats '
                      'INNER JOIN members members1 '
                      'ON (chats.id=members1.chat_id AND members1.member_id=%s) '
                      'INNER JOIN members members2 '
                      'ON (chats.id=members2.chat_id AND members2.member_id=%s) '
                      'WHERE private=1;', *members, fetch_one=True)
        if not res:
            raise PeerNotFound(members)
        return cls(res)

    @property
    def members(self):
        res = sql_req('SELECT member_id FROM `members` WHERE chat_id=%s', self.id, fetch_all=True)
        return [member.get('member_id') for member in res]

    def get_members(self):
        query = 'SELECT users.id, users.first_name, users.last_name, users.profile_picture, users.screen_name FROM `members` ' \
                'INNER JOIN `users` ON member_id=users.id ' \
                'WHERE chat_id=%s'
        res = sql_req(query, self.id, fetch_all=True)
        return [User(user) for user in res]

    def get_messages(self, count=None, offset=None, antichronological=None):
        count = count if count is not None else 20
        offset = offset if offset is not None else 0
        antichronological = antichronological if antichronological is not None else True
        query = 'SELECT messages.*, users.first_name, users.last_name, users.profile_picture, users.screen_name FROM messages ' \
                'INNER JOIN users ON messages.author_id = users.id ' \
                f'WHERE messages.chat_id = %s ORDER BY messages.datetime {"DESC" if antichronological else "ASC"} LIMIT %s OFFSET %s'
        res = sql_req(query, self.id, count, offset, fetch_all=True)
        messages = []
        for message in res:
            _message = Message(message)
            _message.author = User({
                'id': _message.author_id,
                'first_name': message.get('first_name'),
                'last_name': message.get('last_name'),
                'profile_picture': message.get('profile_picture'),
                'screen_name': message.get('screen_name'),
            })
            messages.append(_message)
        return messages

    def get_user_last_read(self, user_id):
        try:
            return sql_req('SELECT last_read FROM `members` WHERE chat_id=%s AND member_id=%s', self.id, user_id, fetch_one=True).get('last_read', 0)
        except KeyError:
            return 0

    @property
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'private': self.private,
            'image': self.image,
            'last_read': self.last_read,
        }

    def assess_access(self, user_id):
        if user_id not in self.members:
            raise PeerNotFound(self.id)

    def add_member(self, user_id):
        from websockets import invite_to_chat
        last_message = self.get_messages(1)
        sql_insert('members', chat_id=self.id, member_id=user_id, last_read=last_message[0].id)
        invite_to_chat(self, user_id, last_message)

    def send_message(self, user_id, text):
        from websockets import send_message_to_chat
        last_id = sql_insert('messages', chat_id=self.id, author_id=user_id, text=text, last_row_id=True)
        message = Message.get(last_id)
        message.mark_as_read(user_id)
        send_message_to_chat(self.id, message)
        return message

    def update(self, **kwargs):
        updates = ','.join([f'{k}=%s' for k in kwargs])
        sql_req(f'UPDATE `chats` SET {updates} WHERE id=%s', *kwargs.values(), self.id)
        vars(self).update(kwargs)
