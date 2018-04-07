"""Views (URL:page refs) for the Denic intranet."""

from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from app.forms import ResetPasswordRequestForm, ResetPasswordForm
from app.forms import AdminValidateAccountForm, SearchOligosForm
from app.forms import InitializeNewRecordsForm, DownloadRecords, EditOligoForm
from app.forms import ConfirmOligoEditsForm, AddNewOligoTable, ConfirmNewOligos
from app.forms import AdminPrivilegesForm, AdminDeleteUserForm
from app.Forms import SearchPlasmidsForm
from app.email import send_password_reset_email
from app.models import User, Oligos, TempOligo, Plasmid, TempPlasmid
from app.models import record_to_dict
from app.output import csv_response
from flask import redirect, url_for, flash, render_template, request, abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from datetime import datetime, date
from functools import wraps
import pandas as pd
import os
from io import StringIO
import random
import string
import jwt
import copy


def admin_required(f):
    """Prevent non-administrators from accessing admin content."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return abort(401)
        return f(*args, **kwargs)
    return decorated_function


def verify_required(f):
    """Prevent unverified users from accessing databases."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.validated:
            return abort(401)
        return f(*args, **kwargs)
    return decorated_function


def flash_errors(form):
    """Flash form errors."""
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')


@app.route('/')
@app.route('/index')
@login_required
def index():
    """Ref to home page."""
    return render_template('index.html', title='Home', posts='')  # TODO:fix


@app.route('/login', methods=['GET', 'POST'])
def login():
    # if user tries to go to this page when they're already logged in
    if current_user.is_authenticated:  # attr from flask_login UserMixin
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():  # activated when submitted
        # use SQLAlchemy query to get record for the user trying to login
        if "@" in form.username.data:  # if logged in using email
            user = User.query.filter_by(email=form.username.data).first()
        else:
            user = User.query.filter_by(username=form.username.data).first()
        # next line checks if user wasn't in db or if the password didn't match
        if user is None or not user.check_password(form.password.data):
            flash('invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        # next, handle redirect to original page if sent by @login_required
        next_page = request.args.get('next')
        # if the user went straight to login (there wasn't a redirect to login)
        # OR! if there was a full URL in the next argument (for security to
        # prevent malicious redirects)
        if not next_page or url_parse(next_page).netloc != '':
            # set it up to redirect to index
            next_page = url_for('index')
        return redirect(next_page)
    # render the login page if the form wasn't submitted already
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.validated = False
        db.session.add(user)
        db.session.commit()
        flash('You have successfully registered. The administrators have been contacted to approve.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = [  # TRM
        {'author': user, 'body': 'Test post #1'},  # TRM
        {'author': user, 'body': 'Test post #2'}   # TRM
    ]  # TRM
    return render_template('user.html', user=user, posts=posts)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/admin/validate', methods=['GET', 'POST'])
@admin_required
def validate_user():
    validate_form = AdminValidateAccountForm()
    admin_form = AdminPrivilegesForm()
    delete_form = AdminDeleteUserForm()
    if validate_form.submit.data:
        user = User.query.filter_by(
            username=validate_form.username.data).first()
        if validate_form.approve.data == 'valid':
            user.validated = True
            db.session.commit()
            flash('User {} has been verified.'.format(user.username))
        elif validate_form.approve.data == 'invalid':
            db.session.delete(user)
            db.session.commit()
            flash('User {} has been deleted.'.format(user.username))
        else:
            flash('You must select an action.')
        return redirect(url_for('validate_user'))
    if admin_form.admin_submit.data:
        user = User.query.filter_by(username=admin_form.username.data).first()
        if admin_form.privileges.data == 'give_admin':
            user.is_admin = True
            db.session.commit()
            flash('User {} now has admin privileges.'.format(user.username))
        elif admin_form.privileges.data == 'remove_admin':
            user.is_admin = False
            db.session.commit()
            flash('User {} set to non-administrator.'.format(user.username))
        else:
            flash('You must select an action.')
        return redirect(url_for('validate_user'))
    if delete_form.delete_submit.data:
        user = User.query.filter_by(
            username=delete_form.username.data).first()
        if delete_form.action.data == 'delete_user':
            db.session.delete(user)
            db.session.commit()
            flash('User {} has been deleted.'.format(user.username))
        else:
            flash('You must select an action.')
        return redirect(url_for('validate_user'))
    return render_template('admin/validate_user.html', title='Validate User',
                           validate_form=validate_form, admin_form=admin_form,
                           delete_form=delete_form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for instructions to reset your password.')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/oligos/begin', methods=['GET', 'POST'])
@login_required
@verify_required
def oligo_search_or_add():
    search_form = SearchOligosForm()
    add_init_form = InitializeNewRecordsForm()
    if search_form.show_all.data or search_form.all_by_me.data or \
       search_form.submit.data:
        if search_form.show_all.data:
            return redirect(url_for(
                'oligo_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'use_range': False, 'oligo_tube': '%'},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.all_by_me.data:
            return redirect(url_for(
                'oligo_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'use_range': False,
                     'creator_id': current_user.id},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.submit.data:
            return redirect(url_for('oligo_search_results', filter_by=mk_query(
                gate=search_form.gate.data,
                use_range=search_form.use_range.data,
                oligo_tube=search_form.oligo_tube.data,
                tube_range_end=search_form.tube_range_end.data,
                oligo_name=search_form.oligo_name.data,
                start_date=search_form.start_date.data,
                end_date=search_form.end_date.data,
                sequence=search_form.sequence.data,
                creator_str=search_form.creator.data,
                restrixn_site=search_form.restrixn_site.data,
                notes=search_form.notes.data
            )))
    if add_init_form.submit_new.data:
        # first make sure there weren't multiple options used
        if add_init_form.input_type.data == 'table_input':
            return redirect(url_for('oligo_add_form',
                                    n_oligos=add_init_form.number_oligos.data))
        elif add_init_form.input_type.data == 'file_input':
            if add_init_form.upload_file.data is None:
                flash('You must upload a file using the browser if you select the Upload File option.')
                return redirect(url_for('oligo_search_or_add'))
            pd_df = pd.read_csv(add_init_form.upload_file.data,
                                delimiter=add_init_form.paste_format.data)
            try:
                new_records = TempOligo.from_pd(
                    pd_df)
                return redirect(url_for('confirm_new_oligos',
                                        temp_ids=[','.join(str(i) for i in
                                                           new_records)]))
            except ValueError:
                flash('The Oligo Name and Sequence columns are required.')
                return redirect(url_for('oligo_search_or_add'))
            return redirect(url_for('confirm_new_oligos',
                                    temp_ids=new_records))
        elif add_init_form.input_type.data == 'paste_input':
            if add_init_form.paste_field.data is None:
                flash('You must paste content into the paste field if you select the Copy-paste table option.')
                return redirect(url_for('oligo_search_or_add'))
            # parse comma-separated or tab-separated data.
            delimiter = add_init_form.paste_format.data
            temp_fname = ''.join(random.choices(string.ascii_uppercase,
                                                k=6)) + '.csv'
            io_obj = StringIO(add_init_form.paste_field.data)
            pd_df = pd.read_csv(io_obj, delimiter=delimiter, header=0)
            pd_df = pd_df.fillna(value='')
            try:
                new_records = TempOligo.from_pd(pd_df)
                return redirect(url_for('confirm_new_oligos',
                                        temp_ids=[','.join(str(i) for i in
                                                           new_records)]))
            except ValueError:
                flash('The Oligo Name and Sequence columns are required.')
                return redirect(url_for('oligo_search_or_add'))
            return redirect(url_for('confirm_new_oligos',
                                    temp_ids=new_records))

    return render_template('oligos/begin.html', search_form=search_form,
                           add_init_form=add_init_form)


@app.route('/oligos/search_results', methods=['GET', 'POST'])
@login_required
@verify_required
def oligo_search_results():
    form = DownloadRecords()
    search_terms = request.args.get('filter_by')
    search_terms = jwt.decode(search_terms, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
    output_records = Oligos.filter_dict_to_records(search_terms)
    if len(output_records) == 0:  # if the search didn't return any items
        flash("Your search did not return any results.")
        return redirect(url_for('oligo_search_or_add'))
    record_list = []
    for r in output_records:
        record_list.append(record_to_dict(r))
    n_records = str(len(record_list))
    if form.validate_on_submit():
        return csv_response(record_list)
    return render_template('oligos/search_results.html',
                           title='Oligo search results',
                           record_list=record_list,
                           form=form,
                           n_records=n_records)


@app.route('/oligos/edit', methods=['GET', 'POST'])
@login_required
@verify_required
def edit_oligo():
    record_id = request.args.get('oligo_tube')
    record_dict = record_to_dict(
        Oligos.query.filter_by(oligo_tube=record_id).first())
    form = EditOligoForm()
    if form.validate_on_submit():
        new_record = Oligos.encode_oligo_dict(
            {'oligo_tube': record_dict['oligo_tube'],
             'oligo_name': form.oligo_name.data,
             'creator_str': form.creator_str.data,
             'sequence': form.sequence.data,
             'restrixn_site': form.restrixn_site.data,
             'notes': form.notes.data}
            )
        return redirect(url_for('confirm_oligo_edits', new_record=new_record))
    else:
        flash_errors(form)
    form.notes.data = record_dict['notes']
    return render_template('oligos/edit_oligo.html', form=form,
                           record_dict=record_dict)


@app.route('/oligos/confirm_edit', methods=['GET', 'POST'])
@login_required
@verify_required
def confirm_oligo_edits():
    new_record = Oligos.decode_oligo_dict(request.args.get('new_record'))
    form = ConfirmOligoEditsForm()
    oligo = Oligos.query.filter_by(oligo_tube=new_record['oligo_tube']).first()
    if form.submit.data:
        oligo.update_record(new_record)
        flash('Your changes to oVD# %s were saved.'
              % new_record['oligo_tube'])
        return redirect(url_for('oligo_search_or_add'))
    if form.go_back.data:
        return redirect(url_for('edit_oligo', oligo_tube=new_record['oligo_tube']))
    for_template = record_to_dict(oligo)
    # update the record dict to include the new values from edits
    for (key, value) in new_record.items():
        for_template[key] = value
    return render_template('oligos/confirm_edits.html', form=form,
                           record_dict=for_template)


@app.route('/oligos/add_oligos_form', methods=['GET', 'POST'])
@login_required
@verify_required
def oligo_add_form():
    n_oligos = int(request.args.get('n_oligos'))
    form = AddNewOligoTable()
    for _ in range(0, n_oligos):
        form.oligos_grid.append_entry()
    if form.validate_on_submit():
        temp_ids = form.to_temp_records()
        return redirect(url_for('confirm_new_oligos',
                                temp_ids=','.join(str(i) for i in temp_ids)))
    return render_template('oligos/add_new_oligos.html', form=form)


@app.route('/oligos/confirm_new_oligos', methods=['GET', 'POST'])
@login_required
@verify_required
def confirm_new_oligos():
    # convert IDs back to list
    temp_ids = [int(i) for i in request.args.get('temp_ids').split(',')]
    form = ConfirmNewOligos()
    record_dicts = [
        record_to_dict(TempOligo.query.filter_by(temp_id=i).first())
        for i in temp_ids
        ]
    if form.validate_on_submit():
        new_oligos = Oligos.new_from_temp(temp_ids)
        return redirect(url_for('show_new_oligos',
                                new_oligos=','.join(str(i) for i in
                                                    new_oligos)))
    return render_template('oligos/confirm_new_oligos.html',
                           record_dicts=record_dicts, form=form)


@app.route('/oligos/complete', methods=['GET'])
@login_required
@verify_required
def show_new_oligos():
    new_oligos = [int(i) for i in request.args.get('new_oligos').split(',')]
    new_records = Oligos.query.filter(Oligos.oligo_tube.in_(new_oligos)).all()
    record_dicts = [record_to_dict(i) for i in new_records]
    return render_template('oligos/complete.html', record_dicts=record_dicts)


@app.route('/plasmids/begin', methods=['GET', 'POST'])
@login_required
@verify_required
def plasmid_search_or_add():
    search_form = SearchPlasmidsForm()  # TODO
    new_plasmid_form = NewPlasmidForm()  # TODO
    if search_form.show_all.data or search_form.all_by_me.data or \
       search_form.submit.data:
        if search_form.show_all.data:
            return redirect(url_for(
                'plasmid_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'use_range': False, 'pVD_number': '%'},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.all_by_me.data:
            return redirect(url_for(
                'plasmid_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'use_range': False,
                     'creator_id': current_user.id},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.submit.data:
            # Handle "Other" options
            if search_form.plasmid_type.data == 'Other':
                plasmid_type = search_form.plasmid_type_other.data
            else:
                plasmid_type = search_form.plasmid_type.data
            if search_form.bac_selection.data == 'Other':
                bac_selection = search_form.bac_sel_other.data
            else:
                bac_selection = search_form.bac_selection.data
            if search_form.yeast_selection.data == 'Other':
                yeast_mamm_selection = search_form.yeast_mamm_sel_other.data
            else:
                yeast_mamm_selection = search_form.yeast_mamm_selection.data
            if search_form.promoter.data == 'Other':
                promoter = search_form.promoter_other.data
            else:
                promoter = search_form.promoter.data
            if search_form.fusion.data == 'Other':
                fusion = search_form.fusion_other.data
            else:
                fusion = search_form.fusion.data

            return redirect(
                url_for('plasmid_search_results', filter_by=mk_query(
                    gate=search_form.gate.data,
                    use_range=search_form.use_range.data,
                    pVD_number=search_form.pVD_number.data,
                    pVD_range_end=search_form.pVD_range_end.data,
                    plasmid_name=search_form.plasmid_name.data,
                    start_date=search_form.start_date.data,
                    end_date=search_form.end_date.data,
                    description=search_form.description.data,
                    creator_str=search_form.creator.data,
                    vector_digest=search_form.vector_digest.data,
                    insert_digest=search_form.insert_digest.data,
                    copy_no_bacteria=search_form.copy_no_bacteria.data,
                    plasmid_type=plasmid_type,
                    bac_selection=bac_selection,
                    yeast_mamm_selection=yeast_mamm_selection,
                    promoter=promoter,
                    fusion=fusion,
                    notes=search_form.notes.data
                    )))
    if new_plasmid_form.new_submit.data:  # TODO: FINISH UPDATING THIS
        if not new_plasmid_form.validate():  # checks if plasmid name is there
            flash_errors(new_plasmid_form)
            return redirect(url_for('plasmid_search_or_add'))
        if 'plasmid_map' in request.files:
            plasmid_map = request.files['plasmid_map']
            map_fname = secure_filename(plasmid_map.filename)
            plasmid_map.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                          map_fname))
        else:
            map_fname = None
        if 'data_file' in request.files:
            data_file = request.files['data_file']
            data_fname = secure_filename(data_file.filename)
            data_file.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                        data_fname))
        else:
            data_fname = None
        new_record = new_plasmid_form.to_temp_record(data_fname, map_fname)
        return redirect(url_for('confirm_new_plasmid'),
                        temp_id=new_record)
    return render_template('plasmids/begin.html', search_form=search_form,
                           new_plasmid_form=new_plasmid_form)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


def mk_query(**kwargs):
    """Generate the SQLAlchemy filter_by argument to search oligo db."""
    return jwt.encode({key: _enc_value(value) for key, value in kwargs.items()
                       if value is not None and value != ''},
                      app.config['SECRET_KEY'],
                      algorithm='HS256').decode('utf-8')


def _enc_value(v):
    if type(v) is str:
        return "%"+v+"%"
    elif type(v) is date:
        return(str(v))
    else:
        return v
