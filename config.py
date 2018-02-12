import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vlad-the-impaler'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql://denic_db_test:Denic08@localhost/oligo_test'  # TODO: UPDATE
    SQLALCHEMY_TRACK_NOTIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['nweir@fas.harvard.edu']  # TODO: UDATE
