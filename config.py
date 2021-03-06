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
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/Users/nweir/Dropbox/code/denic_db/test_uploads/'
    ADMINS = ['nweir@fas.harvard.edu']  # TODO: UDATE
    MAX_CONTENT_LENGTH = 25*1024*1024  # limit max upload size to 25 mb

    # S3 STORAGE #
    USE_S3 = os.environ.get('USE_S3') or 0
    S3_BUCKET = os.environ.get('S3_BUCKET') or None
    S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY') or None
    S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
    S3_LOCATION = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)
