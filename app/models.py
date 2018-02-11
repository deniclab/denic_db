from app import db, login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    oligos = db.relationship('Oligos', backref='Creator', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Oligos(db.Model):
    oligo_tube = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oligo_name = db.Column(db.String(150), index=True)
    date_added = db.Column(db.Date(), index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    sequence = db.Column(db.String(2000))
    restrixn_site = db.Column(db.String(20))
    notes = db.Column(db.String(500))

    def __repr__(self):
        return '<Oligo {}>'.format(self.sequence)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
