from app import db
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import TextAreaField, DateField, SelectField, FieldList, FormField
from wtforms import Form, IntegerField, RadioField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from wtforms.validators import Length
from app.models import User, TempOligo
from flask_login import current_user
from datetime import date


class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('This username exists. Contact the admin.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(
                'An account is already registered to this email. Contact the admin.'
            )


class AdminValidateAccountForm(FlaskForm):
    """Form for administrators to validate new user accounts."""
    def __init__(self):
        """Populate list of users in need of validation."""
        super(AdminValidateAccountForm, self).__init__()
        # next line queries User db for non-validated users and
        # adds them to validate.
        user_list = [(q.username, q.username) for q in
                     User.query.filter_by(validated=False)]
        self.username.choices = user_list
    username = SelectField('New accounts')
    approve = SelectField('Action',
                          choices=[('no_selection', 'Choose one'),
                                   ('valid', 'Validate User'),
                                   ('invalid', 'Invalid - Delete User')])
    submit = SubmitField('Submit')


class AdminPrivilegesForm(FlaskForm):
    """Form to give or remove admin privileges from a user."""
    def __init__(self):
        """Populate list of users in need of validation."""
        super(AdminPrivilegesForm, self).__init__()
        user_list = [(q.username, q.username) for q in
                     User.query.all()]
        self.username.choices = user_list
    username = SelectField('Users')
    privileges = SelectField(
        'Action', choices=[('no_selection', 'Choose one'),
                           ('give_admin', 'Give Admin Privileges'),
                           ('remove_admin', 'Remove Admin Privileges')])
    admin_submit = SubmitField('Submit')


class AdminDeleteUserForm(FlaskForm):
    """Form to remove users. Only allows deletion of non-administrators."""
    def __init__(self):
        """Populate list of users in need of validation."""
        super(AdminDeleteUserForm, self).__init__()
        # next line queries User db for non-administrator users and
        # adds them to validate.
        user_list = [(q.username, q.username) for q in
                     User.query.filter_by(is_admin=False)]
        self.username.choices = user_list
    username = SelectField('Users')
    action = SelectField(
        'Action', choices=[('no_selection', 'Choose one'),
                           ('delete_user', 'Delete user')])
    delete_submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    # TRM NEXT LINE
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please choose a different username.')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Request password reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Complete password reset')


class SearchOligosForm(FlaskForm):
    oligo_tube = StringField('Oligo Tube')
    oligo_name = StringField('Oligo Name')
    start_date = DateField('Date range start, format YYYY-MM-DD')
    end_date = DateField('Date range end, format YYYY-MM-DD')
    sequence = StringField('Sequence')
    creator = StringField('Creator')
    restrixn_site = StringField('Restriction Site')
    notes = TextAreaField('Notes')
    submit = SubmitField('Search')
    show_all = SubmitField('Show All Oligos')
    all_by_me = SubmitField('Show All of My Oligos')


class EditOligoForm(FlaskForm):
    oligo_name = StringField('Oligo Name', validators=[DataRequired(),
                                                       Length(max=150)])
    sequence = StringField('Sequence', validators=[Length(max=2000)])
    creator_str = StringField('Creator', validators=[Length(max=50)])
    restrixn_site = StringField('Restriction Site',
                                validators=[Length(max=20)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Submit changes')


class ConfirmOligoEditsForm(FlaskForm):
    submit = SubmitField('Confirm changes')
    go_back = SubmitField('Go Back')


class InitializeNewOligosForm(FlaskForm):
    input_type = RadioField('Choose input type',
                            choices=[('table_input', 'Form'),
                                     ('file_input', 'Upload file'),
                                     ('paste_input', 'Copy-paste table')],
                            validators=[DataRequired()])
    number_oligos = IntegerField('Number of new oligos (form entry only)')
    upload_file = FileField('Upload .csv or .txt file',
                            validators=[FileAllowed(
                                ['csv', 'txt'],
                                'Only csv and txt allowed.')])

    paste_field = TextAreaField('Paste comma- or tab-separated values here')
    paste_format = RadioField('Delimiter', choices=[('\t', 'Tab'),
                                                    (',', 'Comma')],
                              default=',')
    submit_new = SubmitField('Submit')


class AddNewOligoRecord(Form):
    oligo_name = StringField('Oligo Name',
                             validators=[Length(max=150)])
    creator = StringField('Creator')
    sequence = StringField('Sequence', validators=[
                                                   Length(max=2000)])
    restrixn_site = StringField('Restriction Site',
                                validators=[Length(max=20)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])

    def validate(self):
        if not Form.validate(self):
            return False
        if bool(self.oligo_name.data) != bool(self.sequence.data):
            self.oligo_name.errors.append('Oligo name and sequence required.')
            return False
        return True


class AddNewOligoTable(FlaskForm):

    oligos_grid = FieldList(FormField(AddNewOligoRecord),
                            min_entries=0)
    submit = SubmitField('Submit')

    def to_temp_records(self):
        """Create TempOligos records from values. Returns list of db IDs."""
        record_ids = []
        for entry in self.oligos_grid.entries:  # iterate over rows in grid
            if entry.oligo_name.data:  # if the row contains an oligo name
                new_record = TempOligo(oligo_name=entry.oligo_name.data,
                                       creator_str=entry.creator.data,
                                       creator_id=current_user.id,
                                       sequence=entry.sequence.data,
                                       restrixn_site=entry.restrixn_site.data,
                                       notes=entry.notes.data)
                db.session.add(new_record)
                db.session.commit()
                record_ids.append(new_record.temp_id)
        return record_ids  # use this as a ref to retrieve records later


class ConfirmNewOligos(FlaskForm):
    submit = SubmitField('Add to Database')


class DownloadRecords(FlaskForm):
    download = SubmitField("Download to CSV")
