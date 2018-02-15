from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import TextAreaField, DateField, SelectField, FieldList, FormField
from wtforms import IntegerField, RadioField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from wtforms.validators import Length
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
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
    pass  # TODO: Implement.


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


class InitializeNewOligosForm(FlaskForm):
    input_type = RadioField('Choose input type',
                            choices=[('table_input', 'Form'),
                                     ('file_input', 'Upload file'),
                                     ('paste_input', 'Copy-paste table')])
    number_oligos = IntegerField('Number of new oligos (form entry only)')
    upload_file = FileField('Upload .csv or .xlsx-format file',
                            validators=[FileAllowed(
                                ['csv', 'txt', 'xls', 'xlsx'],
                                'Only csv, txt, and Excel files allowed.')])

    paste_field = TextAreaField('Paste comma- or tab-separated values here')
    paste_format = RadioField('Delimiter', choices=[('\t', 'Tab'),
                                                    (',', 'Comma')])
    submit = SubmitField('Submit')


class AddNewOligoRecord(FlaskForm):
    oligo_name = StringField('Oligo Name',
                             validators=[DataRequired(), Length(max=150)])
    creator = SelectField('Creator')  # TODO: NEED TO IMPLEMENT CHOICES IN VIEWS
    date_added = DateField('Date added, format YYYY-MM-DD')
    sequence = StringField('Sequence', validators=[Length(max=2000)])
    restrixn_site = StringField('Restriction Site',
                                validators=[Length(max=20)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])


class AddNewOligoTable(FlaskForm):
    grid_oligo_records = FieldList(FormField(AddNewOligoRecord), min_entries=1)
    submit = SubmitField('Create')


class DownloadRecords(FlaskForm):
    download = SubmitField("Download to CSV")
