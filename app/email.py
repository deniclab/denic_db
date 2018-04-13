from app import app, mail
from flask import render_template
from flask_mail import Message
from threading import Thread
from app.models import User


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Denic Intranet] Reset your password',
               sender=app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token)
               )


def send_validation_request_email(user):
    new_username = user.username
    new_email = user.email
    send_email('[Denic Intranet] New user validation request',
               sender=app.config['ADMINS'][0],
               recipients=[a.email for a in
                           User.query.filter_by(is_admin=True).all()],
               text_body=render_template('email/validation_request.txt',
                                         new_username=new_username,
                                         new_email=new_email),
               html_body=render_template('email/validation_request.html',
                                         new_username=new_username,
                                         new_email=new_email))
