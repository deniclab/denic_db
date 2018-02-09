import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vlad-the-impaler'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql://denic_db_test:Denic08@localhost/oligo_test'  # TODO: UPDATE
    SQLALCHEMY_TRACK_NOTIFICATIONS = False
