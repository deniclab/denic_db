"""Views (URL:page refs) for the Denic intranet."""

from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from app.forms import ResetPasswordRequestForm, ResetPasswordForm
from app.forms import AdminValidateAccountForm
from app.email import send_password_reset_email
from app.models import User
from flask import redirect, url_for, flash, render_template, request
from flask import abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from datetime import datetime
from functools import wraps
import pandas as pd


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


@app.route('/oligos', methods=['GET', 'POST'])
@app.route('/oligos/begin', methods=['GET', 'POST'])
@verify_required
def oligo_search_or_add():
    search_form = SearchOligosForm()
    add_init_form = InitializeNewOligosForm()
    if search_form.validate_on_submit():
        pass  # TODO: IMPLEMENT THIS!
    if add_init_form.validate_on_submit():
        pass  # TODO: IMPLEMENT THIS!


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
