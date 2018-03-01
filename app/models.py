from app import app, db, login
from datetime import datetime, date
from time import time
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
import pandas as pd
from hashlib import md5


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    oligos = db.relationship('Oligos', backref='Creator', lazy='dynamic')
    about_me = db.Column(db.String(140))  # TRM
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    validated = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size
        )

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


class Oligos(db.Model):
    oligo_tube = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oligo_name = db.Column(db.String(150), index=True)
    date_added = db.Column(db.Date(), index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    creator_str = db.Column(db.String(50))
    sequence = db.Column(db.String(2000))
    restrixn_site = db.Column(db.String(20))
    notes = db.Column(db.String(500))

    def __repr__(self):
        return '<Oligo {}>'.format(self.oligo_tube)

    def update_record(self, record_dict):
        for (key, value) in record_dict.items():
            if key is not 'oligo_tube':
                if getattr(self, key) != value:
                    setattr(self, key, value)
        db.session.commit()

    @staticmethod
    def new_from_temp(temp_ids):
        """Add records from the TempOligo table, returning their new IDs."""
        new_tubes = []
        for i in temp_ids:
            temp_oligo = TempOligo.query.filter_by(temp_id=i).first()
            new_record = Oligos(oligo_name=temp_oligo.oligo_name,
                                date_added=date.today(),
                                creator_id=current_user.id,
                                creator_str=temp_oligo.creator_str,
                                sequence=temp_oligo.sequence,
                                restrixn_site=temp_oligo.restrixn_site,
                                notes=temp_oligo.notes)
            db.session.add(new_record)
            db.session.commit()
            new_tubes.append(new_record.oligo_tube)
        return new_tubes

    @staticmethod
    def filter_dict_to_records(filter_dict):
        """Take a dictionary of column:search_term pairs and get records."""
        return Oligos.query.filter(
            *(getattr(Oligos, key).ilike(value) for (key, value)
              in filter_dict.items())).all()


    @staticmethod
    def encode_oligo_dict(oligo_dict):
        """jwt-encode an oligo dict to send thru URL."""
        return jwt.encode(oligo_dict, app.config['SECRET_KEY'],
                          algorithm='HS256')

    @staticmethod
    def decode_oligo_dict(token):
        """decode jwt-encoded dictionary of oligo record."""
        return jwt.decode(token, app.config['SECRET_KEY'],
                          algorithms=['HS256'])


class TempOligo(db.Model):
    temp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oligo_tube = db.Column(db.Integer, db.ForeignKey('oligos.oligo_tube'),
                           index=True)
    oligo_name = db.Column(db.String(150), index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    creator_str = db.Column(db.String(50))
    sequence = db.Column(db.String(2000))
    restrixn_site = db.Column(db.String(20))
    notes = db.Column(db.String(500))

    @staticmethod
    def from_pd(record_df):
        """Add new records from uploaded .csv, .txt, or copy-paste input."""
        # make sure the required column is present
        record_df.columns = [x.lower() for x in record_df.columns]
        if 'oligo name' not in list(record_df.columns.values):
            raise ValueError('Oligo name column required.')
        record_dict = record_df.to_dict(orient='records')
        new_ids = []
        for row in record_dict:
            new_oligo = TempOligo(
                oligo_name=row['oligo name'].strip(),
                creator_id=current_user.id,
                creator_str=row.get('creator', '').strip(),
                sequence=row.get('sequence', '').strip(),
                restrixn_site=row.get('restriction site', '').strip(),
                notes=row.get('notes', '').strip())
            db.session.add(new_oligo)
            db.session.commit()
            new_ids.append(new_oligo.temp_id)
        return new_ids


def record_to_dict(record):
    """Convert a SQLAlchemy record output object to a dict of values."""
    r_dict = record.__dict__
    r_dict.pop('_sa_instance_state', None)
    return r_dict


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
