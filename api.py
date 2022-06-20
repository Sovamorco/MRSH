from methods import *


vers = {
    '0.0.1': {
        'register_user': RegisterUser_0_0_1,
        'create_chat': CreateChat_0_0_1,
        'send_message': SendMessage_0_0_1,
    },
    '0.0.2': {
        'register_user': RegisterUser_0_0_2,
        'login_user': LoginUser_0_0_2,
        'verify_email': VerifyEmail_0_0_2,
        'get_chats': GetChats_0_0_2,
        'get_chat': GetChat_0_0_2,
        'create_chat': CreateChat_0_0_2,
        'deny_verification': DenyVerification_0_0_2,
    },
    '0.0.3': {
        'create_chat': CreateChat_0_0_3,
        'add_friend': AddFriend_0_0_3,
        'remove_friend': RemoveFriend_0_0_3,
        'get_friends': GetFriends_0_0_3,
        'invite_to_chat': InviteToChat_0_0_3,
        'send_message': SendMessage_0_0_3,
        'mark_as_read': MarkAsRead_0_0_3,
        'get_user': GetUser_0_0_3,
    },
    '0.0.4': {
        'send_message': SendMessage_0_0_4,
        'resend_verification': ResendVerification_0_0_4,
        'get_chats': GetChats_0_0_4,
        'get_chat_history': GetChatHistory_0_0_4,
    },
    '0.0.5': {
        'change_profile_picture': ChangeProfilePicture_0_0_5,
        'set_settings': SetSettings_0_0_5,
        'change_chat_image': ChangeChatImage_0_0_5,
        'get_chat': GetChat_0_0_5,
        'get_chats': GetChats_0_0_5,
        'get_chat_history': GetChatHistory_0_0_5,
    }
}


websocket_methods = set(filter(None, [subc.name for subc in AuthorizedMethod.__subclasses__()]))


def find_method(version, method):
    versions = list(vers.keys())
    ind = versions.index(version)
    for v in reversed(versions[0:ind + 1]):
        if method in vers[v]:
            return vers[v][method]
    raise InvalidMethod


def api_request(**kwargs):
    v = kwargs.pop('version', LATEST_VERSION)
    if v not in vers:
        raise InvalidVersion
    method = kwargs.pop('method', None)
    return find_method(v, method)().process(**kwargs)
