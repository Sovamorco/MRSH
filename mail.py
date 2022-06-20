from flask_mail import Mail, Message
from pyisemail import is_email
from pyisemail.validators.dns_validator import dns

from api_exceptions import *

mail = Mail()


def send_email(target, topic, message):
    try:
        if not is_email(target, True):
            raise BadEmail(target)
    except dns.resolver.NoNameservers:
        raise BadEmail(target)
    msg = Message(topic,
                  sender=('MRSH', "noreply@sovamor.co"),
                  recipients=[target], body=message)
    mail.send(msg)


def verification_email(target, vercode):
    send_email(target, 'Email Verification', 'MRSH sign-up is almost over. All that`s left is to verify your e-mail.'
                                             '\nTo do that, please follow this link:'
                                             f'\n{API_URL}/verify_email?code={vercode}'
                                             '\n'
                                             '\nIf you didn`t create an account, please click on the following link:'
                                             f'\n{API_URL}/deny_verification?code={vercode}')
