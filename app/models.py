from app import app, db, login, forms
from sqlalchemy import or_
from datetime import datetime, date
from time import time
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
import pandas as pd
from hashlib import md5
import re


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
        """Take a dictionary of column:search_term pairs and get records.

        `filter_dict` must contain two keys:
            gate : str
                should the filter utilize and AND or an OR gate across
                the arguments. Note that if a tube range is used, it is
                always used in an AND gate fashion.
            use_range : bool
                should a range of oligo tubes be searched. If true,
                all other filters are applied first, and then the
                results are filtered by the tube range.
        """
        gate = filter_dict.pop('gate')
        gate = gate.strip('%')  # see views.mk_query and views._enc_value
        use_range = filter_dict.pop('use_range')
        oligo_tube = filter_dict.pop('oligo_tube', None)
        tube_range_end = filter_dict.pop('tube_range_end', None)
        date_range_start = filter_dict.pop('start_date', None)
        date_range_end = filter_dict.pop('end_date', date.today())
        # generate initial query which does not include oligo tube filtering
        if gate == 'OR':
            query_result = Oligos.query.filter(or_(
                *(getattr(Oligos, key).ilike(value) for (key, value)
                  in filter_dict.items())))
        else:
            query_result = Oligos.query.filter(
                *(getattr(Oligos, key).ilike(value) for (key, value)
                  in filter_dict.items()))
        # add date range filtering to the query
        if date_range_start is not None:
            query_result = query_result.filter(
                (Oligos.date_added >= date_range_start) &
                (Oligos.date_added <= date_range_end))
        # add oligo tube filtering to the query
        if oligo_tube is not None:
            if use_range:
                query_result = query_result.filter(
                    (Oligos.oligo_tube >= oligo_tube.strip("%")) &
                    (Oligos.oligo_tube <= tube_range_end.strip("%")))
            else:
                query_result = query_result.filter(
                    Oligos.oligo_tube.ilike(oligo_tube))
        return query_result.all()

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
        if not set(('oligo name', 'sequence')).issubset(set(
                record_df.columns.values)):
            raise ValueError('Oligo name and sequence columns required.')
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


class Plasmid(db.Model):
    pVD_number = db.Column(db.Integer, primary_key=True, autoincrement=True)
    plasmid_name = db.Column(db.String(150), index=True)
    date_added = db.Column(db.Date(), index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    creator_str = db.Column(db.String(50))
    simple_description = db.Column(db.String(200))
    backbone = db.Column(db.String(50))
    insert_source = db.Column(db.String(50))
    vector_digest = db.Column(db.String(100))
    insert_digest = db.Column(db.String(100))
    copy_no_bacteria = db.Column(db.String(5))
    plasmid_type = db.Column(db.String(50))
    bac_selection = db.Column(db.String(25))
    yeast_mamm_selection = db.Column(db.String(50))
    promoter = db.Column(db.String(50))
    fusion = db.Column(db.String(50))
    sequenced = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(2000))
    # because plasmid map and data are renamed to match pVD number,
    # just need a boolean indicator of whether or not it's present
    image_filename = db.Column(db.String(100))
    map_filename = db.Column(db.String(100))

    def __repr__(self):
        return '<Plasmid {}>'.format(self.pVD_number)

    def update_record(self, record_dict):
        for (key, value) in record_dict.items():
            if key is not 'pVD_number':
                if getattr(self, key) != value:
                    setattr(self, key, value)
        db.session.commit()

    @staticmethod
    def filter_dict_to_records(filter_dict):
        """Take a dictionary of column:search_term pairs and get records.

        `filter_dict` must contain two keys:
            gate : str
                should the filter utilize and AND or an OR gate across
                the arguments. Note that if a tube range is used, it is
                always used in an AND gate fashion.
            use_range : bool
                should a range of plasmid tubes be searched. If true,
                all other filters are applied first, and then the
                results are filtered by the tube range.
        """
        gate = filter_dict.pop('gate')
        gate = gate.strip('%')  # see views.mk_query and views._enc_value
        use_range = filter_dict.pop('use_range')
        pVD_number = filter_dict.pop('pVD_number', None)
        pVD_range_end = filter_dict.pop('pVD_range_end', None)
        date_range_start = filter_dict.pop('start_date', None)
        date_range_end = filter_dict.pop('end_date', date.today())
        # generate initial query which does not include oligo tube filtering
        if gate == 'OR':
            query_result = Plasmid.query.filter(or_(
                *(getattr(Plasmid, key).ilike(value) for (key, value)
                  in filter_dict.items())))
        else:
            query_result = Plasmid.query.filter(
                *(getattr(Plasmid, key).ilike(value) for (key, value)
                  in filter_dict.items()))
        # get the list of relatives from the relative table
        if 'relative' in filter_dict:
            relative_list = app.forms.NewPlasmidForm.relative_field_to_pVDs(
                filter_dict.pop('relative'))
            relation_query = PlasmidRelative.query.filter(
                or_(((PlasmidRelative.pVD_number.like(i)),
                    (PlasmidRelative.parent_plasmid.like(i)))
                    for i in relative_list))
            relative_pvds = [
                relation.pVD_number for relation in relation_query.all()]
            if gate == 'OR':
                plasmid_relatives = Plasmid.query.filter(
                    Plasmid.pVD_number.in_(relative_pvds))
                query_result = query_result.union(plasmid_relatives)
        # add date range filtering to the query
        if date_range_start is not None:
            query_result = query_result.filter(
                (Plasmid.date_added >= date_range_start) &
                (Plasmid.date_added <= date_range_end))
        # add oligo tube filtering to the query
        if pVD_number is not None:
            if use_range:
                query_result = query_result.filter(
                    (Plasmid.pVD_number >= pVD_number.strip("%")) &
                    (Plasmid.pVD_number <= pVD_range_end.strip("%")))
            else:
                query_result = query_result.filter(
                    Plasmid.pVD_number.ilike(pVD_number))
        return query_result.all()

    def new_from_temp(temp_id):
        """Add a record from TempPlasmid, returning its new pVD number."""
        temp_plasmid = TempPlasmid.query.filter_by(temp_id=temp_id).first()
        new_record = Plasmid(
            plasmid_name=temp_plasmid.plasmid_name,
            date_added=date.today(),
            creator_id=current_user.id,
            creator_str=temp_plasmid.creator_str,
            simple_description=temp_plasmid.simple_description,
            vector_digest=temp_plasmid.vector_digest,
            insert_digest=temp_plasmid.insert_digest,
            backbone=temp_plasmid.backbone,
            insert_source=temp_plasmid.insert_source,
            copy_no_bacteria=temp_plasmid.copy_no_bacteria,
            plasmid_type=temp_plasmid.plasmid_type,
            bac_selection=temp_plasmid.bac_selection,
            yeast_mamm_selection=temp_plasmid.yeast_mamm_selection,
            promoter=temp_plasmid.promoter,
            fusion=temp_plasmid.fusion,
            image_filename=temp_plasmid.image_filename,
            map_filename=temp_plasmid.map_filename,
            sequenced=temp_plasmid.sequenced,
            notes=temp_plasmid.notes)
        db.session.add(new_record)
        db.session.commit()
        return new_record.pVD_number


class PlasmidRelative(db.Model):
    """SQLAlchemy model for recording plasmid parents and descendants."""

    relation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pVD_number = db.Column(db.Integer, db.ForeignKey('plasmid.pVD_number'))
    parent_plasmid = db.Column(db.Integer)

    @staticmethod
    def string_to_pVDs(relative_field):
        """Extract list of relative pVD numbers from the relative field."""
        return [int(i) for i in re.findall('[0-9]+', relative_field)]

    @staticmethod
    def pVD_list_to_records(pVD_child, pVD_parent_list):
        """Takes string of relative pVD numbers and creates parent records."""
        if pVD_parent_list:
            for p in pVD_parent_list:
                parent_record = PlasmidRelative(pVD_number=pVD_child,
                                                parent_plasmid=p)
                db.session.add(parent_record)
                db.session.commit()


class TempPlasmid(db.Model):
    temp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pVD_number = db.Column(db.Integer, db.ForeignKey('plasmid.pVD_number'),
                           index=True)
    plasmid_name = db.Column(db.String(150), index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    creator_str = db.Column(db.String(50))
    simple_description = db.Column(db.String(200))
    vector_digest = db.Column(db.String(100))
    insert_digest = db.Column(db.String(100))
    backbone = db.Column(db.String(25))
    insert_source = db.Column(db.String(50))
    copy_no_bacteria = db.Column(db.String(5))
    plasmid_type = db.Column(db.String(50))
    bac_selection = db.Column(db.String(25))
    yeast_mamm_selection = db.Column(db.String(25))
    promoter = db.Column(db.String(50))
    fusion = db.Column(db.String(50))
    image_filename = db.Column(db.String(100))
    map_filename = db.Column(db.String(100))
    sequenced = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(2000))
    parent = db.Column(db.String(100))


def record_to_dict(record):
    """Convert a SQLAlchemy record output object to a dict of values."""
    r_dict = record.__dict__
    r_dict.pop('_sa_instance_state', None)
    return r_dict


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
