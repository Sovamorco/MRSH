from flask import request
from flask_socketio import SocketIO, send, ConnectionRefusedError, join_room, leave_room

import mrsh_json
from objects import *

socketio = SocketIO(path=f'/{APP_NAME}/websocket', json=mrsh_json, cors_allowed_origins='*', async_mode='gevent')

socketio.clients = {}


def validate_token():
    auth = request.headers.get('Authorization')
    if not auth or ' ' not in auth:
        raise ConnectionRefusedError('Unauthorized.')
    token = auth.split(' ', 1)[1]
    try:
        user = User.authorize_by_token(token)
    except InvalidTokenError:
        raise ConnectionRefusedError('Unauthorized.')
    return user


@socketio.event
def connect():
    user = validate_token()
    if user.id not in socketio.clients:
        socketio.clients[user.id] = []
    socketio.clients[user.id].append(request.sid)
    for chat in user.get_chats():
        join_room(f'chat{chat.id}')
    send({'status': 'connected', 'response': user})


@socketio.event
def disconnect():
    for user in socketio.clients:
        if request.sid in socketio.clients[user]:
            socketio.clients[user].remove(request.sid)


def _join_chat(user_id, chat_id):
    for sid in socketio.clients.get(user_id, []):
        join_room(f'chat{chat_id}', sid=sid, namespace='/')


def _leave_chat(user_id, chat_id):
    for sid in socketio.clients.get(user_id, []):
        leave_room(f'chat{chat_id}', sid=sid, namespace='/')


def _emit_to_user(user_id, *args, **kwargs):
    for sid in socketio.clients.get(user_id, []):
        socketio.emit(*args, room=sid, **kwargs)


def send_message_to_chat(chat_id, message):
    socketio.emit('new_message', message, room=f'chat{chat_id}')


def invite_to_chat(chat, user, last_message):
    _join_chat(user, chat.id)
    _emit_to_user(user, 'chat_invite', {
        **chat.to_dict,
        'last_message': last_message,
    })


def removed_from_chat(chat, user):
    _leave_chat(chat, user)
    _emit_to_user(user, 'chat_removed', chat)


def add_friend(user, target_id, accepted):
    _emit_to_user(target_id, 'friend_request', (user, accepted))


def remove_friend(user, target_id, requested):
    _emit_to_user(target_id, 'friend_removed', (user, requested))


def change_settings(user, changed):
    _emit_to_user(user.id, 'settings_changed', changed)


def read_message(message):
    socketio.emit('message_read', message, room=f'chat{message.chat_id}')
