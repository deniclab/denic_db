"""Views (URL:page refs) for the Denic intranet."""

from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from app.forms import ResetPasswordRequestForm, ResetPasswordForm
from app.forms import AdminValidateAccountForm, SearchOligosForm
from app.forms import InitializeNewOligosForm, DownloadRecords, EditOligoForm
from app.forms import ConfirmOligoEditsForm
from app.email import send_password_reset_email
from app.models import User, Oligos
from app.output import csv_response
from flask import redirect, url_for, flash, render_template, request, abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import pandas as pd
import os
from io import StringIO
import random
import string
import jwt


def admin_required(f):
    """Decorator to prevent non-administrators from accessing admin content."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return abort(401)
        return f(*args, **kwargs)
    return decorated_function


def verify_required(f):
    """Decorator to prevent unverified users from accessing databases."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.validated:
            return abort(401)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html', title='Home', posts='')  # TODO:fix

@app.route('/login', methods=['GET', 'POST'])
def login():
    # if user tries to go to this page when they're already logged in
    if current_user.is_authenticated:  # attr from flask_login UserMixin
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():  # activated when submitted
        # use SQLAlchemy query to get record for the user trying to login
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
    form = AdminValidateAccountForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if form.approve.data == 'valid':
            user.validated = True
            db.session.commit()
            flash('User {} has been verified'.format(user.username))
        elif form.approve.data == 'invalid':
            db.session.delete(user)
            db.session.commit()
            flash('User {} has been deleted'.format(user.username))
        return redirect(url_for('admin/validate'))
    return render_template('admin/validate_user.html', title='Validate User',
                           form=form)


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
    add_init_form = InitializeNewOligosForm()
    if search_form.show_all or search_form.all_by_me or search_form.submit:
        if search_form.show_all.data:
            return redirect(url_for(
                'search_results',
                filter_by=jwt.encode({}, app.config['SECRET_KEY'],
                                     algorithm='HS256').decode('utf-8')))
        if search_form.all_by_me.data:
            return redirect(url_for(
                'search_results',
                filter_by=jwt.encode({'creator_id': current_user.id},
                                     app.config['SECRET_KEY'],
                                     algorithm='HS256').decode('utf-8')))
        if search_form.submit.data:
            return redirect(url_for('search_results', filter_by=mk_query(
                oligo_tube=search_form.oligo_tube.data,
                oligo_name=search_form.oligo_name.data,
                start_date=search_form.start_date.data,
                end_date=search_form.end_date.data,
                sequence=search_form.sequence.data,
                creator_str=search_form.creator.data,
                restrixn_site=search_form.restrixn_site.data,
                notes=search_form.notes.data
            )))
    if add_init_form.validate_on_submit():
        # first make sure there weren't multiple options used
        if add_init_form.upload_file.data is not None and \
                add_init_form.paste_field.data is not None:
            flash('You must use either upload or paste, not both.')
            return redirect(url_for('oligo_search_or_add'))
        if add_init_form.upload_file.data is not None:
            f = add_init_form.upload_file.data
            # TODO: IMPLEMENT FILE TYPE READING/CONVERSION HERE AS NEEDED
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('check_oligos', filename=filename))
        if add_init_form.paste_field.data is not None:
            # parse comma-separated or tab-separated data.
            delimiter = add_init_form.paste_format.data
            temp_fname = random.choices(string.ascii_uppercase, k=6) + '.csv'
            io_obj = StringIO(add_init_form.paste_field.data)
            pd_df = pd.read_csv(io_obj, delimiter=delimiter, header=0)
            pd_df.to_csv(os.path.join(app.config['UPLOAD_FOLDER'], temp_fname),
                         index=False)
            return redirect(url_for('check_oligos', filename=temp_fname))
        if add_init_form.number_oligos.data is not None:
            return redirect(url_for('oligo_add_form',
                                    n_oligos=add_init_form.number_oligos.data))
    return render_template('oligos/begin.html', search_form=search_form,
                           add_init_form=add_init_form)


@app.route('/oligos/search_results', methods=['GET', 'POST'])
@login_required
@verify_required
def search_results():
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
        record_list.append(Oligos.record_to_dict(r))
    if form.validate_on_submit():
        return csv_response(record_list)
    return render_template('oligos/search_results.html',
                           title='Oligo search results',
                           record_list=record_list,
                           form=form)


@app.route('/oligos/edit', methods=['GET', 'POST'])
@login_required
@verify_required
def edit_oligo():
    record_id = request.args.get('oligo_tube')
    record_dict = Oligos.record_to_dict(
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
    for_template = Oligos.record_to_dict(oligo)
    # update the record dict to include the new values from edits
    for (key, value) in new_record.items():
        for_template[key] = value
    return render_template('oligos/confirm_edits.html', form=form,
                           record_dict=for_template)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


def mk_query(**kwargs):
    """Generate the SQLAlchemy filter_by argument to search oligo db."""
    return jwt.encode({key: "%"+value+"%" for key, value in kwargs.items()
                       if value is not None}, app.config['SECRET_KEY'],
                      algorithm='HS256').decode('utf-8')
