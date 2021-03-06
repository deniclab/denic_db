"""Views (URL:page refs) for the Denic intranet."""

from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from app.forms import ResetPasswordRequestForm, ResetPasswordForm
from app.forms import AdminValidateAccountForm, SearchOligosForm
from app.forms import InitializeNewRecordsForm, DownloadRecords, EditOligoForm
from app.forms import ConfirmOligoEditsForm, AddNewOligoTable, ConfirmNewOligos
from app.forms import SearchPlasmidsForm, NewPlasmidForm, EditPlasmidForm
from app.forms import AdminPrivilegesForm, AdminDeleteUserForm
from app.forms import SearchStrainsForm, NewStrainForm, EditStrainForm
from app.email import send_password_reset_email, send_validation_request_email
from app.models import User, Oligos, TempOligo, Strain, StrainGenotype
from app.models import Plasmid, TempPlasmid, PlasmidRelative, StrainRelative
from app.models import TempStrain, TempStrainGenotype, record_to_dict
from app.helpers import upload_file_to_s3, download_file_from_s3
from app.output import csv_response
from flask import redirect, url_for, flash, render_template, request, abort
from flask import send_from_directory, make_response
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
        send_validation_request_email(user)
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
@login_required
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
                    {'gate': 'OR', 'oligo_tube': '%'},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.all_by_me.data:
            return redirect(url_for(
                'oligo_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'creator_id': current_user.id},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.submit.data:
            return redirect(url_for('oligo_search_results', filter_by=mk_query(
                gate=search_form.gate.data,
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
            if add_init_form.number_oligos.data is None:
                flash('You must indicate how many oligos you are adding.')
                return redirect(url_for('oligo_search_or_add'))
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
        return csv_response(record_list, 'oligos')
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
        return redirect(url_for('edit_oligo',
                                oligo_tube=new_record['oligo_tube']))
    for_template = record_to_dict(oligo)
    # update the record dict to include the new values from edits
    for (key, value) in new_record.items():
        if key == 'date_added':
            continue
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
    search_form = SearchPlasmidsForm()
    new_plasmid_form = NewPlasmidForm()
    if search_form.show_all.data or search_form.all_by_me.data or \
       search_form.submit.data:
        if search_form.show_all.data:
            return redirect(url_for(
                'plasmid_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'pVD_number': '%'},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.all_by_me.data:
            return redirect(url_for(
                'plasmid_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'creator_id': current_user.id},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.submit.data:
            # Handle "Other" options
            if search_form.plasmid_type_other.data:
                plasmid_type = search_form.plasmid_type_other.data
            else:
                plasmid_type = search_form.plasmid_type.data
            if search_form.bac_sel_other.data:
                bac_selection = search_form.bac_sel_other.data
            else:
                bac_selection = search_form.bac_selection.data
            if search_form.yeast_mamm_sel_other.data:
                yeast_mamm_selection = search_form.yeast_mamm_sel_other.data
            else:
                yeast_mamm_selection = search_form.yeast_mamm_selection.data
            if search_form.promoter_other.data:
                promoter = search_form.promoter_other.data
            else:
                promoter = search_form.promoter.data
            if search_form.fusion_other.data:
                fusion = search_form.fusion_other.data
            else:
                fusion = search_form.fusion.data
            return redirect(
                url_for('plasmid_search_results', filter_by=mk_query(
                    gate=search_form.gate.data,
                    pVD_number=search_form.pVD_number.data,
                    pVD_range_end=search_form.pVD_range_end.data,
                    plasmid_name=search_form.plasmid_name.data,
                    start_date=search_form.start_date.data,
                    end_date=search_form.end_date.data,
                    simple_description=search_form.description.data,
                    creator_str=search_form.creator.data,
                    vector_digest=search_form.vector_digest.data,
                    insert_digest=search_form.insert_digest.data,
                    backbone=search_form.backbone.data,
                    insert_source=search_form.insert_source.data,
                    copy_no_bacteria=search_form.copy_no_bacteria.data,
                    plasmid_type=plasmid_type,
                    bac_selection=bac_selection,
                    yeast_mamm_selection=yeast_mamm_selection,
                    promoter=promoter,
                    fusion=fusion,
                    notes=search_form.notes.data,
                    relative=search_form.relative.data
                    )))
    if new_plasmid_form.new_submit.data:  # TODO: FINISH UPDATING THIS
        if not new_plasmid_form.validate():  # checks if plasmid name is there
            flash_errors(new_plasmid_form)
            return redirect(url_for('plasmid_search_or_add'))
        if 'plasmid_map' in request.files:
            plasmid_map = request.files['plasmid_map']
            map_fname = secure_filename(plasmid_map.filename)
            if app.config['USE_S3']:
                plasmid_map.filename = map_fname
                upload_file_to_s3(plasmid_map, app.config['S3_BUCKET'],
                                  folder=app.config['UPLOAD_FOLDER'])
            else:
                plasmid_map.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                              map_fname))
        else:
            map_fname = None
        if 'data_file' in request.files:
            data_file = request.files['data_file']
            data_fname = secure_filename(data_file.filename)
            if app.config['USE_S3']:
                data_file.filename = data_fname
                upload_file_to_s3(data_file, app.config['S3_BUCKET'],
                                  folder=app.config['UPLOAD_FOLDER'])
            else:
                data_file.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                            data_fname))
        else:
            data_fname = None
        new_record = new_plasmid_form.to_temp_record(data_fname, map_fname)
        return redirect(url_for('confirm_new_plasmid',
                        temp_id=new_record))
    return render_template('plasmids/begin.html', search_form=search_form,
                           new_plasmid_form=new_plasmid_form)


@app.route('/plasmids/search_results', methods=['GET', 'POST'])
@login_required
@verify_required
def plasmid_search_results():
    form = DownloadRecords()
    search_terms = request.args.get('filter_by')
    search_terms = jwt.decode(search_terms, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
    output_records = Plasmid.filter_dict_to_records(search_terms)
    if len(output_records) == 0:  # if the search didn't return any items
        flash("Your search did not return any results.")
        return redirect(url_for('plasmid_search_or_add'))
    record_list = []
    for r in output_records:
        record_list.append(record_to_dict(r))
    n_records = str(len(record_list))
    if form.validate_on_submit():
        return csv_response(record_list, 'plasmids')
    return render_template('plasmids/search_results.html',
                           title='Plasmid search results',
                           record_list=record_list,
                           form=form,
                           n_records=n_records)


@app.route('/plasmids/confirm_new_plasmid', methods=['GET', 'POST'])
@login_required
@verify_required
def confirm_new_plasmid():
    # convert IDs back to list
    temp_id = int(request.args.get('temp_id'))
    form = ConfirmNewOligos()  # this is just a submit button
    record_dict = record_to_dict(
        TempPlasmid.query.filter_by(temp_id=temp_id).first())
    record_dict['parent'] = PlasmidRelative.string_to_pVDs(
        record_dict['parent'])  # convert from string to list
    if form.validate_on_submit():
        new_plasmid = Plasmid.new_from_temp(temp_id)
        PlasmidRelative.pVD_list_to_records(new_plasmid, record_dict['parent'])
        return redirect(url_for('show_new_plasmid',
                                new_plasmid=new_plasmid))
    return render_template('plasmids/confirm_new_plasmid.html',
                           record_dict=record_dict, form=form)


@app.route('/plasmids/show_new_plasmid', methods=['GET'])
@login_required
@verify_required
def show_new_plasmid():
    new_plasmid = request.args.get('new_plasmid')
    new_record = Plasmid.query.filter_by(pVD_number=new_plasmid).first()
    record_dict = record_to_dict(new_record)
    parent_plasmids = PlasmidRelative.query.filter_by(
        pVD_number=new_record.pVD_number).all()
    parent_plasmids = ['pVD'+str(p.parent_plasmid) for p in parent_plasmids]
    parent_plasmids = ', '.join(parent_plasmids)
    return render_template('plasmids/complete.html', record_dict=record_dict,
                           parent_plasmids=parent_plasmids)


@app.route('/plasmids/edit', methods=['GET', 'POST'])
@login_required
@verify_required
def edit_plasmid():
    record_id = request.args.get('pVD_number')
    record_dict = record_to_dict(
        Plasmid.query.filter_by(pVD_number=record_id).first())
    form = EditPlasmidForm()
    if form.download_map.data:
        return redirect(url_for('download_plasmid_file'),
                        pVD_number=record_id, type='map')
    if form.download_data.data:
        return redirect(url_for('download_plasmid_file'),
                        pVD_number=record_id, type='data')
    if form.submit.data and form.validate():
        output_dict = record_dict
        output_dict.pop('date_added', '')
        if form.plasmid_type_other.data:
            form.plasmid_type.data = form.plasmid_type_other.data
            form.plasmid_type_other.data = None
        if form.bac_sel_other.data:
            form.bac_selection.data = form.bac_sel_other.data
            form.bac_sel_other.data = None
        if form.yeast_mamm_sel_other.data:
            form.yeast_mamm_selection.data = form.yeast_mamm_sel_other.data
            form.yeast_mamm_sel_other.data = None
        if form.promoter_other.data:
            form.promoter.data = form.promoter_other.data
            form.promoter_other.data = None
        if form.fusion_other.data:
            form.fusion.data = form.fusion_other.data
            form.fusion_other.data = None
        for fieldname, value in form.data.items():
            if fieldname in ('plasmid_map', 'data_file', 'submit',
                             'csrf_token', 'download_map', 'download_data',
                             'date_added'):
                continue  # these fields handled later (or left out)
            if value not in ('', None, 'None'):
                output_dict[fieldname] = value
        if 'plasmid_map' in request.files:
            plasmid_map = request.files['plasmid_map']
            map_fname = secure_filename(plasmid_map.filename)
            if app.config['USE_S3']:
                plasmid_map.filename = map_fname
                upload_file_to_s3(plasmid_map, app.config['S3_BUCKET'],
                                  folder=app.config['UPLOAD_FOLDER'])
            else:
                plasmid_map.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                              map_fname))
            output_dict['map_filename'] = map_fname
        else:
            map_fname = None
        if 'data_file' in request.files:
            data_file = request.files['data_file']
            data_fname = secure_filename(data_file.filename)
            if app.config['USE_S3']:
                data_file.filename = data_fname
                upload_file_to_s3(data_file, app.config['S3_BUCKET'],
                                  folder=app.config['UPLOAD_FOLDER'])
            else:
                data_file.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                            data_fname))
            output_dict['image_filename'] = data_fname
        else:
            data_fname = None
        new_record = Oligos.encode_oligo_dict(output_dict)  # jwt dict encoder
        return redirect(url_for(
            'confirm_plasmid_edits', new_record=new_record,
            map_fname=map_fname, data_fname=data_fname))
    else:
        flash_errors(form)
    parent_plasmids = [str(i.parent_plasmid) for i in
                       PlasmidRelative.query.filter_by(pVD_number=record_id)]
    parent_plasmids = ','.join(parent_plasmids)
    form.notes.data = record_dict['notes']
    form.parents.data = parent_plasmids
    # TODO: ADD LINES HERE TO PASS VALS TO RELATIVE FIELD
    return render_template('plasmids/edit_plasmid.html', form=form,
                           record_dict=record_dict)


@app.route('/plasmids/confirm_edit', methods=['GET', 'POST'])
@login_required
@verify_required
def confirm_plasmid_edits():
    new_record = Oligos.decode_oligo_dict(request.args.get('new_record'))
    form = ConfirmOligoEditsForm()  # this is just 2 submit buttons
    plasmid = Plasmid.query.filter_by(
        pVD_number=new_record['pVD_number']).first()
    if form.submit.data:
        parent_plasmids = new_record.pop('parents', '')
        parent_plasmids = PlasmidRelative.string_to_pVDs(parent_plasmids)
        # first, check if records exist that match the listed parents, and
        # if records exist for the same pVD that have other parents which
        # need to be removed.
        db_parents = PlasmidRelative.query.filter_by(
            pVD_number=plasmid.pVD_number).all()
        db_parent_list = [p.parent_plasmid for p in db_parents]
        for d in db_parents:
            # remove the ones that aren't in the list passed by the user
            if d.parent_plasmid not in parent_plasmids:
                db.session.delete(d)
                db.session.commit()
        for p in parent_plasmids:
            # add the ones that aren't already in the PlasmidRelative table
            if p not in db_parent_list:
                new_parent = PlasmidRelative(pVD_number=plasmid.pVD_number,
                                             parent_plasmid=p)
                db.session.add(new_parent)
                db.session.commit()
        plasmid.update_record(new_record)
        flash('Your changes to pVD# %s were saved.'
              % new_record['pVD_number'])
        return redirect(url_for('plasmid_search_or_add'))
    if form.go_back.data:
        return redirect(url_for('edit_plasmid',
                                pVD_number=new_record['pVD_number']))
    for_template = record_to_dict(plasmid)
    # update the record dict to include the new values from edits
    for (key, value) in new_record.items():
        for_template[key] = value
    return render_template('plasmids/confirm_edits.html', form=form,
                           record_dict=for_template)


@app.route('/plasmids/download', methods=['GET'])
@login_required
@verify_required
def download_plasmid_file():
    pVD_number = request.args.get('pVD_number')
    file_type = request.args.get('type')
    record = Plasmid.query.filter_by(pVD_number=pVD_number).first()
    if file_type == 'map':
        if app.config['USE_S3']:
            f = download_file_from_s3(
                record.map_filename, app.config['S3_BUCKET'],
                app.config['UPLOAD_FOLDER'])
            response = make_response(f['Body'].read())
            response.headers['Content-Disposition'] = 'attachment;filename='+record.map_filename
            response.headers['Content-Type'] = f['ContentType']
            return response
        else:
            return send_from_directory(
                app.config['UPLOAD_FOLDER'],
                record.map_filename, as_attachment=True,
                attachment_filename=record.map_filename)
    elif file_type == 'data':
        if app.config['USE_S3']:
            f = download_file_from_s3(
                record.image_filename, app.config['S3_BUCKET'],
                app.config['UPLOAD_FOLDER'])
            response = make_response(f['Body'].read())
            response.headers['Content-Disposition'] = 'attachment;filename='+record.image_filename
            response.headers['Content-Type'] = f['ContentType']
            return response
        else:
            return send_from_directory(
                app.config['UPLOAD_FOLDER'],
                record.image_filename, as_attachment=True,
                attachment_filename=record.image_filename)


@app.route('/strains/begin', methods=['GET', 'POST'])
@login_required
@verify_required
def strain_search_or_add():
    search_form = SearchStrainsForm()
    new_strain_form = NewStrainForm()
    if search_form.show_all.data or search_form.all_by_me.data or \
       search_form.submit.data:
        if search_form.show_all.data:
            return redirect(url_for(
                'strain_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'genotype_gate': 'OR', 'VDY_number': '%',
                     'find_all': True},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.all_by_me.data:
            return redirect(url_for(
                'strain_search_results',
                filter_by=jwt.encode(
                    {'gate': 'OR', 'genotype_gate': 'OR',
                     'creator_id': current_user.id},
                    app.config['SECRET_KEY'],
                    algorithm='HS256').decode('utf-8')))
        if search_form.submit.data:
            return redirect(
                url_for('strain_search_results', filter_by=mk_query(
                    gate=search_form.gate.data,
                    VDY_number=search_form.VDY_number.data,
                    VDY_range_end=search_form.VDY_range_end.data,
                    other_names=search_form.other_names.data,
                    start_date=search_form.start_date.data,
                    end_date=search_form.end_date.data,
                    origin=search_form.origin.data,
                    creator_str=search_form.creator.data,
                    strain_background=search_form.strain_background.data,
                    notebook_ref=search_form.notebook_ref.data,
                    marker=search_form.marker.data,
                    genotype=['%' + entry.genotype.data + '%' for entry in
                              search_form.genotype_list.entries if
                              entry.genotype.data],
                    genotype_gate=search_form.genotype_gate.data,
                    notes=search_form.notes.data,
                    parent_strain=search_form.parent.data,
                    plasmid=search_form.plasmid.data,
                    plasmid_selexn=search_form.plasmid_selexn.data
                    )))
    if new_strain_form.new_submit.data:  # TODO: FINISH UPDATING THIS
        if not new_strain_form.validate():  # checks if plasmid name is there
            flash_errors(new_strain_form)
            return redirect(url_for('strain_search_or_add'))
        # save data file
        if 'data_file' in request.files:
            data_file = request.files['data_file']
            data_fname = secure_filename(data_file.filename)
            # use AWS S3 storage for deployment version
            if app.config['USE_S3']:
                data_file.filename = data_fname
                upload_file_to_s3(data_file, app.config['S3_BUCKET'],
                                  folder=app.config['UPLOAD_FOLDER'])
            # use preset upload folder for dev version
            else:
                data_file.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                            data_fname))
        else:
            data_fname = None
        new_record = new_strain_form.to_temp_record(data_fname)
        return redirect(url_for('confirm_new_strain',
                        temp_id=new_record))
    return render_template('strains/begin.html', search_form=search_form,
                           new_strain_form=new_strain_form)


@app.route('/strains/search_results', methods=['GET', 'POST'])
@login_required
@verify_required
def strain_search_results():
    form = DownloadRecords()
    search_terms = request.args.get('filter_by')
    search_terms = jwt.decode(search_terms, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
    output_records = Strain.filter_dict_to_records(search_terms)
    if len(output_records) == 0:  # if the search didn't return any items
        flash("Your search did not return any results.")
        return redirect(url_for('strain_search_or_add'))
    record_list = []
    for r in output_records:
        record = record_to_dict(r)
        genotypes = [gt.locus_info for gt in StrainGenotype.query.filter_by(
            VDY_number=r.VDY_number).all()]
        record_list.append({'record': record, 'genotypes': genotypes})

    n_records = str(len(record_list))
    if form.validate_on_submit():
        return csv_response([r['record'] for r in record_list], 'strains')
    return render_template('strains/search_results.html',
                           title='Strain search results',
                           record_list=record_list,
                           form=form,
                           n_records=n_records)


@app.route('/strains/edit', methods=['GET', 'POST'])
@login_required
@verify_required
def edit_strain():
    strain_val_dict = {'0': 'Not Validated', '1': 'Colony PCR',
                       '2': 'Western Blot', '3': 'Sequencing',
                       '4': 'Microscopy', '5': 'Other'}
    record_id = request.args.get('VDY_number')
    record_dict = record_to_dict(
        Strain.query.filter_by(VDY_number=record_id).first())
    genotypes = [gt.locus_info for gt in StrainGenotype.query.filter_by(
        VDY_number=record_id).all()]
    if record_dict['validation'] is not None:
        validation_str = ', '.join([strain_val_dict[i] for i in record_dict['validation'].split(',')])
    else:
        validation_str = 'None'
    descendants = [d.VDY_number for d in
                   StrainRelative.query.filter_by(
                       parent_strain=record_id).all()]
    form = EditStrainForm()
    if form.download_data.data:
        return redirect(url_for('download_strain_file'),
                        VDY_number=record_id)
    if form.submit.data and form.validate():
        output_dict = record_dict
        output_dict.pop('date_added')
        for fieldname, value in form.data.items():
            if fieldname in ('date_added', 'data_file', 'submit', 'csrf_token',
                             'download_data', 'validation'):
                continue  # these fields handled later (or left out)
            if value not in ('', None, 'None'):
                output_dict[fieldname] = value
        if 'data_file' in request.files:
            data_file = request.files['data_file']
            data_fname = secure_filename(data_file.filename)
            if app.config['USE_S3']:
                data_file.filename = data_fname
                upload_file_to_s3(data_file, app.config['S3_BUCKET'],
                                  folder=app.config['UPLOAD_FOLDER'])
            else:
                data_file.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                            data_fname))
            output_dict['image_filename'] = data_fname
        else:
            data_fname = None
        if form.validation.data:
            output_dict['validation'] = ','.join(form.validation.data)

        new_record = Oligos.encode_oligo_dict(output_dict)  # jwt dict encoder
        return redirect(url_for(
            'confirm_strain_edits', new_record=new_record,
            data_fname=data_fname))
    else:
        flash_errors(form)
    parent_strains = [str(i.parent_strain) for i in
                      StrainRelative.query.filter_by(VDY_number=record_id)]
    parent_strains_str = ','.join(parent_strains)
    form.notes.data = record_dict['notes']
    form.parent_strain.data = parent_strains_str
    # TODO: ADD LINES HERE TO PASS VALS TO RELATIVE FIELD
    return render_template('strains/edit_strain.html', form=form,
                           record_dict=record_dict, descendants=descendants,
                           validation=validation_str,
                           parent_strains=parent_strains,
                           genotypes=genotypes)


@app.route('/strains/confirm_edit', methods=['GET', 'POST'])
@login_required
@verify_required
def confirm_strain_edits():
    strain_val_dict = {'0': 'Not Validated', '1': 'Colony PCR',
                       '2': 'Western Blot', '3': 'Sequencing',
                       '4': 'Microscopy', '5': 'Other'}
    new_record = Oligos.decode_oligo_dict(request.args.get('new_record'))
    form = ConfirmOligoEditsForm()  # this is just 2 submit buttons
    if new_record['validation']:
        validation_str = ', '.join([strain_val_dict[v] for v in
                                    new_record['validation'].split(',')])
    else:
        validation_str = 'None'
    strain = Strain.query.filter_by(
        VDY_number=new_record['VDY_number']).first()
    if form.submit.data:
        parent_strains = new_record.pop('parent_strain', '')
        if parent_strains is not None:
            parent_strains = PlasmidRelative.string_to_pVDs(parent_strains)
            # first, check if records exist that match the listed parents, and
            # if records exist for the same pVD that have other parents which
            # need to be removed.
            db_parents = StrainRelative.query.filter_by(
                VDY_number=strain.VDY_number).all()
            db_parent_list = [p.parent_strain for p in db_parents]
            for d in db_parents:
                # remove the ones that aren't in the list passed by the user
                if d.parent_strain not in parent_strains:
                    db.session.delete(d)
            for p in parent_strains:
                # add the ones that aren't already in the PlasmidRelative table
                if p not in db_parent_list:
                    new_parent = StrainRelative(VDY_number=strain.VDY_number,
                                                parent_strain=p)
                    db.session.add(new_parent)
        db.session.commit()
        genotypes = [g['genotype'] for g in new_record.pop('genotype_list') if
                     g['genotype']]  # eliminates empty strings
        db_genotypes = StrainGenotype.query.filter_by(
            VDY_number=strain.VDY_number).all()
        db_genotypes_list = [dg.locus_info for dg in db_genotypes]
        for d in db_genotypes:
            if d.locus_info not in genotypes:
                db.session.delete(d)
        for g in genotypes:
            if g not in db_genotypes_list:
                new_genotype = StrainGenotype(VDY_number=strain.VDY_number,
                                              locus_info=g)
                db.session.add(new_genotype)
        db.session.commit()
        strain.update_record(new_record)
        flash('Your changes to VDY# %s were saved.'
              % new_record['VDY_number'])
        return redirect(url_for('strain_search_or_add'))
    if form.go_back.data:
        return redirect(url_for('edit_strain',
                                VDY_number=new_record['VDY_number']))
    for_template = record_to_dict(strain)
    # update the record dict to include the new values from edits
    for (key, value) in new_record.items():
        for_template[key] = value
    return render_template('strains/confirm_edits.html', form=form,
                           record_dict=for_template, validation=validation_str
                           )


@app.route('/strains/confirm_new_strain', methods=['GET', 'POST'])
@login_required
@verify_required
def confirm_new_strain():
    strain_val_dict = {'0': 'Not Validated', '1': 'Colony PCR',
                       '2': 'Western Blot', '3': 'Sequencing',
                       '4': 'Microscopy', '5': 'Other'}
    # convert IDs back to list
    temp_id = int(request.args.get('temp_id'))
    temp_genotypes = TempStrainGenotype.query.filter_by(
        temp_strain_id=temp_id).all()
    temp_genotype_list = [tg.locus_info for tg in temp_genotypes]
    form = ConfirmNewOligos()  # this is just a submit button
    record_dict = record_to_dict(
        TempStrain.query.filter_by(temp_id=temp_id).first())
    if record_dict['validation'] is not None:
        validation_str = ', '.join(
            [strain_val_dict[v] for v in
             record_dict['validation'].split(',')])
    if form.validate_on_submit():
        new_strain = Strain.new_from_temp(temp_id)
        return redirect(url_for('show_new_strain',
                                new_strain=new_strain))
    return render_template('strains/confirm_new_strain.html',
                           record_dict=record_dict,
                           validation=validation_str,
                           genotypes=temp_genotype_list, form=form)


@app.route('/strains/show_new_strain', methods=['GET'])
@login_required
@verify_required
def show_new_strain():
    strain_val_dict = {'0': 'Not Validated', '1': 'Colony PCR',
                       '2': 'Western Blot', '3': 'Sequencing',
                       '4': 'Microscopy', '5': 'Other'}
    new_strain = request.args.get('new_strain')
    new_record = Strain.query.filter_by(VDY_number=new_strain).first()
    record_dict = record_to_dict(new_record)
    if record_dict['validation'] is not None:
        validation_str = ', '.join(
            [strain_val_dict[v] for v in
             record_dict['validation'].split(',')])
    parent_strains = [p.parent_strain for p in StrainRelative.query.filter_by(
        VDY_number=new_record.VDY_number).all()]
    genotypes = StrainGenotype.query.filter_by(VDY_number=new_strain).all()
    genotypes = [gt.locus_info for gt in genotypes]
    return render_template('strains/complete.html', record_dict=record_dict,
                           parent_strains=parent_strains, genotypes=genotypes,
                           validation=validation_str)


@app.route('/strains/download', methods=['GET'])
@login_required
@verify_required
def download_strain_file():
    VDY_number = request.args.get('VDY_number')
    record = Strain.query.filter_by(VDY_number=VDY_number).first()
    if app.config['USE_S3']:
        f = download_file_from_s3(
            record.image_filename, app.config['S3_BUCKET'],
            app.config['UPLOAD_FOLDER'])
        response = make_response(f['Body'].read())
        response.headers['Content-Disposition'] = 'attachment;filename='+record.image_filename
        response.headers['Content-Type'] = f['ContentType']
        return response
    else:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            record.image_filename, as_attachment=True,
            attachment_filename=record.image_filename)


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
