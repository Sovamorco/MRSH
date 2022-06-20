from common import get_secrets

secrets = get_secrets(
    'flask_app_secret',
    'sql_host',
    'sql_port',
    'sql_user',
    'sql_password',
)
