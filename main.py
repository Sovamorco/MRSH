from flask import Blueprint, jsonify

from api import *

app = Blueprint(APP_NAME, __name__, static_url_path='')
app.secret_key = secrets['flask_app_secret']


@app.route(f'/{APP_NAME}/api/<method>', methods=['GET', 'POST'])
def api(method):
    kwargs = dict(request.values)
    if request.json:
        kwargs.update(request.json)
    if request.files:
        kwargs.update(request.files)
    try:
        res = api_request(method=method, **kwargs)
    except InvalidRequest as e:
        return jsonify(success=False, error={'code': e.code, 'string': e.string, 'message': e.message})
    return jsonify(success=True, response=res)


def websocket_api_callback(method):
    def _inner(kwargs=None):
        if kwargs is None:
            kwargs = {}
        auth = request.headers.get('Authorization', '')
        if 'token' not in kwargs and ' ' in auth:
            kwargs['token'] = auth.split(' ', 1)[1]
        try:
            res = api_request(method=method, **kwargs)
        except InvalidRequest as e:
            return {'success': False, 'error': {'code': e.code, 'string': e.string, 'message': e.message}}
        return {'success': True, 'response': res}

    return _inner


for _method in websocket_methods:
    socketio.on_event(_method, websocket_api_callback(_method))
