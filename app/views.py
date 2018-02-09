"""Views (URL:page refs) for the Denic intranet."""

from app import app
from flask import session, redirect, url_for, flash, render_template
from app.forms import LoginForm


@app.route('/')
@app.route('/index')
def home():
    user = {'username': 'Nick'}  # mock user
        # TODO: FINISH IMPLEMENTING THIS FUNCTION.


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('home'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been successfully logged out.')
    return redirect(url_for('home'))
