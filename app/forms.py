from app import db
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import TextAreaField, DateField, SelectField, FieldList, FormField
from wtforms import Form, IntegerField, RadioField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from wtforms.validators import Length
from app.models import User, TempOligo, TempPlasmid, TempStrain
from app.models import TempStrainGenotype
from app.helpers import MultiCheckboxField
from flask_login import current_user
from datetime import date
import re


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
    gate = RadioField('', choices=[
        ('OR', 'ANY of these fields (ex. created by Vlad OR with Get3 in the name)'),
        ('AND', 'ALL of these fields (ex. created by Vlad AND with Get3 in the name)')],
                      default='OR', validators=[DataRequired()])
    oligo_tube = StringField('Oligo Tube')
    tube_range_end = StringField('Tube range end')
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


class InitializeNewRecordsForm(FlaskForm):
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
                if not entry.creator.data:
                    entry.creator.data = current_user.username
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


class SearchPlasmidsForm(FlaskForm):
    # Note: Many of the fields in this form are statically defined in the HTML
    # to allow option grouping in select fields. Therefore, changing
    # SelectField options here won't necessarily change them in the website,
    # and the changes may need to additionally be defined in
    # templates/plasmids/begin.html .
    gate = RadioField('', choices=[
        ('OR', 'ANY of the following fields (ex. Amp selection OR Yeast CEN/ARS plasmid)'),
        ('AND', 'ALL of the following fields (ex. Amp selection AND Yeast CEN/ARS plasmid)')],
                      default='OR', validators=[DataRequired()])
    pVD_number = StringField('pVD Number')
    pVD_range_end = StringField('pVD range end')
    plasmid_name = StringField('Plasmid Name')
    start_date = DateField('Date range start, format YYYY-MM-DD')
    end_date = DateField('Date range end, format YYYY-MM-DD')
    description = StringField('Description')
    creator = StringField('Plasmid creator/source')
    backbone = StringField('Plasmid backbone')
    insert_source = StringField('Source of insert')
    vector_digest = StringField('Vector digest')
    insert_digest = StringField('Insert digest')
    copy_no_bacteria = SelectField('Bacterial copy no.',
                                   choices=[
                                       ('', 'Select one'),
                                       ('Low', 'Low'), ('High', 'High')],
                                   default='')
    plasmid_type = SelectField('Plasmid Type', choices=[
        ('', 'Select one'),
        ('Cloning vector', 'Cloning vector'),
        ('E. coli expression', 'E. coli expression'), ('BAC', 'BAC'),
        ('Yeast CEN/ARS', 'Yeast CEN/ARS'),
        ('Yeast 2 Micron', 'Yeast 2 Micron'),
        ('Yeast Integrating', 'Yeast Integrating'),
        ('YAC', 'YAC'),
        ('Mammalian Transient Expression', 'Mammalian Transient Expression'),
        ('Mammalian Retroviral', 'Mammalian Retroviral'),
        ('Mammalian Lentiviral', 'Mammalian Lentiviral'),
        ('Mammalian Integrating', 'Mammalian Integrating')], default='')
    plasmid_type_other = StringField('Other')
    bac_selection = SelectField('Bacterial selection', choices=[
        ('', 'Select one'),
        ('None', 'None'), ('Amp', 'Amp/Carb'), ('Cm', 'Cm'), ('Kn', 'Kan'),
        ('Neo', 'Neo'), ('Phleo', 'Phleo'), ('Spec', 'Spec'), ('Tet', 'Tet')], default='')
    bac_sel_other = StringField('Other')
    yeast_mamm_selection = SelectField('Yeast/Mammalian selection', choices=[
        ('', 'Select one'), ('NA', 'Not applicable'),
        ('TRP', 'TRP'), ('HIS', 'HIS'), ('URA', 'URA'), ('LEU', 'LEU'),
        ('KAN', 'KAN'), ('NAT', 'NAT'), ('yHYG', 'HYG (Yeast)'),
        ('Blasticidin', 'Blasticidin'), ('mHYG', 'HYG (Mammalian)'),
        ('Neo', 'Neo'), ('Puro', 'Puro'), ('Zeo', 'Zeo')], default='')
    yeast_mamm_sel_other = StringField('Other')
    promoter = SelectField('Promoter', choices=[
        ('', 'Select one'),
        ('pGAL', 'pGAL'), ('pTDH3', 'pTDH3/pGPD'), ('pZ4EV', 'pZ4EV'),
        ('pZ3EV', 'pZ3EV'), ('pTET', 'pTET'), ('pCUP', 'pCUP'),
        ('pMET', 'pMET'), ('CMV', 'CMV'), ('CAG', 'CAG'), ('MSCV', 'MSCV'),
        ('Psyn1', 'Psyn1'), ('Psyn135', 'Psyn135'), ('PT7', 'PT7'),
        ('PR', 'PR'), ('Plac', 'Plac'), ('Ptac', 'Ptac'), ('Para', 'Para')], default='')
    promoter_other = StringField('Other')
    fusion = SelectField('Fusion', choices=[
        ('', 'Select one'),
        ('GFP', '(e)GFP'), ('YFP', '(e)YFP/Citrine'), ('RFP', 'RFP/mCherry'),
        ('CFP', '(e)CFP'), ('mTurquoise2', 'mTurquoise2'), ('sfGFP', 'sfGFP'),
        ('sfYFP', 'sfYFP'), ('mNeongreen', 'mNeongreen'),
        ('BFP', 'BFP/TagBFP(2)'), ('mEOS', 'mEOS variant'), ('Myc', 'Myc'),
        ('HA', 'HA'), ('FLAG', 'FLAG'), ('6His', '6His'), ('10His', '10His'),
        ('MBP', 'MBP'), ('GST', 'GST'), ('SUMO', 'SUMO'), ('MalE', 'MalE'),
        ('SBP', 'SBP'), ('BiFC', 'BiFC fragment'), ('Gal4', 'Y2H (Gal4)'),
        ('Ubi', 'Y2H (Ubi)')],
                         default='')
    fusion_other = StringField('Other')
    notes = TextAreaField('Notes')
    relative = StringField('Relative pVD #')
    submit = SubmitField('Search')
    show_all = SubmitField('Show All Plasmids')
    all_by_me = SubmitField('Show All Plasmids I entered')


class NewPlasmidForm(FlaskForm):
    # Note: Many of the fields in this form are statically defined in the HTML
    # to allow option grouping in select fields. Therefore, changing
    # SelectField options here won't necessarily change them in the website,
    # and the changes may need to additionally be defined in
    # templates/plasmids/begin.html .
    # Note that all field names are prefaced with "new" to distinguish them
    # from fields in the search form.
    new_plasmid_name = StringField('Plasmid Name', validators=[DataRequired()])
    new_description = StringField('Description')
    new_creator = StringField('Plasmid creator/source')
    new_backbone = StringField('Plasmid backbone')
    new_insert_source = StringField('Source of insert')
    new_vector_digest = StringField('Vector digest')
    new_insert_digest = StringField('Insert digest')
    new_copy_no_bacteria = SelectField(
        'Bacterial copy no.', choices=[('', 'Select one'),
                                       ('Low', 'Low'), ('High', 'High')],
        default='')
    new_plasmid_type = SelectField('Plasmid Type', choices=[
        ('', 'Select one'),
        ('Cloning vector', 'Cloning vector'),
        ('E. coli expression', 'E. coli expression'), ('BAC', 'BAC'),
        ('Yeast CEN/ARS', 'Yeast CEN/ARS'),
        ('Yeast 2 Micron', 'Yeast 2 Micron'),
        ('Yeast Integrating', 'Yeast Integrating'),
        ('YAC', 'YAC'),
        ('Mammalian Transient Expression', 'Mammalian Transient Expression'),
        ('Mammalian Retroviral', 'Mammalian Retroviral'),
        ('Mammalian Lentiviral', 'Mammalian Lentiviral'),
        ('Mammalian Integrating', 'Mammalian Integrating')], default='')
    new_plasmid_type_other = StringField('Other')
    new_bac_selection = SelectField('Bacterial selection', choices=[
        ('', 'Select one'),
        ('None', 'None'), ('Amp', 'Amp/Carb'), ('Cm', 'Cm'), ('Kn', 'Kan'),
        ('Neo', 'Neo'), ('Phleo', 'Phleo'), ('Spec', 'Spec'), ('Tet', 'Tet')], default='')
    new_bac_sel_other = StringField('Other')
    new_yeast_mamm_selection = SelectField(
        'Yeast/Mammalian selection', choices=[
            ('', 'Select one'), ('NA', 'Not applicable'),
            ('TRP', 'TRP'), ('HIS', 'HIS'), ('URA', 'URA'), ('LEU', 'LEU'),
            ('KAN', 'KAN'), ('NAT', 'NAT'), ('yHYG', 'HYG (Yeast)'),
            ('Blasticidin', 'Blasticidin'), ('mHYG', 'HYG (Mammalian)'),
            ('Neo', 'Neo'), ('Puro', 'Puro'), ('Zeo', 'Zeo')], default='')
    new_yeast_mamm_sel_other = StringField('Other')
    new_promoter = SelectField('Promoter', choices=[
        ('', 'Select one'),
        ('pGAL', 'pGAL'), ('pTDH3', 'pTDH3/pGPD'), ('pZ4EV', 'pZ4EV'),
        ('pZ3EV', 'pZ3EV'), ('pTET', 'pTET'), ('pCUP', 'pCUP'),
        ('pMET', 'pMET'), ('CMV', 'CMV'), ('CAG', 'CAG'), ('MSCV', 'MSCV'),
        ('Psyn1', 'Psyn1'), ('Psyn135', 'Psyn135'), ('PT7', 'PT7'),
        ('PR', 'PR'), ('Plac', 'Plac'), ('Ptac', 'Ptac'), ('Para', 'Para')],
                               default='')
    new_promoter_other = StringField('Other')
    new_fusion = SelectField('Fusion', choices=[
        ('', 'Select one'),
        ('GFP', '(e)GFP'), ('YFP', '(e)YFP/Citrine'), ('RFP', 'RFP/mCherry'),
        ('CFP', '(e)CFP'), ('mTurquoise2', 'mTurquoise2'), ('sfGFP', 'sfGFP'),
        ('sfYFP', 'sfYFP'), ('mNeongreen', 'mNeongreen'),
        ('BFP', 'BFP/TagBFP(2)'), ('mEOS', 'mEOS variant'), ('Myc', 'Myc'),
        ('HA', 'HA'), ('FLAG', 'FLAG'), ('6His', '6His'), ('10His', '10His'),
        ('MBP', 'MBP'), ('GST', 'GST'), ('SUMO', 'SUMO'), ('MalE', 'MalE'),
        ('SBP', 'SBP'), ('BiFC', 'BiFC fragment'), ('Gal4', 'Y2H (Gal4)'),
        ('Ubi', 'Y2H (Ubi)')],
                             default='')
    new_fusion_other = StringField('Other')
    new_notes = TextAreaField('Notes')
    new_parent = StringField('Comma-separated parent pVD #s')
    plasmid_map = FileField('Upload Plasmid Map (.gb preferred)')
    data_file = FileField('Upload Relevant Data File (<25 MB)')
    sequenced = BooleanField('Insert sequenced?')
    new_submit = SubmitField('Submit')

    def to_temp_record(self, data_fname, map_fname):
        """Create entry in TempPlasmid table and return id."""
        if self.new_plasmid_type_other.data:
            self.new_plasmid_type.data = self.new_plasmid_type_other.data
        if self.new_bac_sel_other.data:
            self.new_bac_selection.data = self.new_bac_sel_other.data
        if self.new_yeast_mamm_sel_other.data:
            self.new_yeast_mamm_selection.data =\
                self.new_yeast_mamm_sel_other.data
        if self.new_promoter_other.data:
            self.new_promoter.data = self.new_promoter_other.data
        if self.new_fusion_other.data:
            self.new_fusion.data = self.new_fusion_other.data
        # handle empty creator string
        if not self.new_creator.data:
            self.new_creator.data = current_user.username
        new_record = TempPlasmid(
            plasmid_name=self.new_plasmid_name.data,
            creator_id=current_user.id,
            creator_str=self.new_creator.data,
            simple_description=self.new_description.data,
            backbone=self.new_backbone.data,
            insert_source=self.new_insert_source.data,
            vector_digest=self.new_vector_digest.data,
            insert_digest=self.new_insert_digest.data,
            copy_no_bacteria=self.new_copy_no_bacteria.data,
            plasmid_type=self.new_plasmid_type.data,
            bac_selection=self.new_bac_selection.data,
            yeast_mamm_selection=self.new_yeast_mamm_selection.data,
            promoter=self.new_promoter.data,
            fusion=self.new_fusion.data,
            image_filename=data_fname,
            map_filename=map_fname,
            sequenced=self.sequenced.data,
            notes=self.new_notes.data,
            parent=self.new_parent.data)
        db.session.add(new_record)
        db.session.commit()
        return new_record.temp_id


class EditPlasmidForm(FlaskForm):
    plasmid_name = StringField('Plasmid Name', validators=[DataRequired(),
                                                           Length(max=150)])
    simple_description = StringField('Description',
                                     validators=[Length(max=200)])
    creator_str = StringField('Creator', validators=[Length(max=50)])
    backbone = StringField('Backbone', validators=[Length(max=50)])
    insert_source = StringField('Source of insert',
                                validators=[Length(max=50)])
    vector_digest = StringField('Vector digest', validators=[Length(max=100)])
    insert_digest = StringField('Insert digest', validators=[Length(max=100)])
    copy_no_bacteria = SelectField('Bacterial copy no.',
                                   choices=[
                                       ('', 'Select one'),
                                       ('Low', 'Low'), ('High', 'High')],
                                   default='')
    plasmid_type = SelectField('Plasmid Type', choices=[
        ('', 'Select one'),
        ('Cloning vector', 'Cloning vector'),
        ('E. coli expression', 'E. coli expression'), ('BAC', 'BAC'),
        ('Yeast CEN/ARS', 'Yeast CEN/ARS'),
        ('Yeast 2 Micron', 'Yeast 2 Micron'),
        ('Yeast Integrating', 'Yeast Integrating'),
        ('YAC', 'YAC'),
        ('Mammalian Transient Expression', 'Mammalian Transient Expression'),
        ('Mammalian Retroviral', 'Mammalian Retroviral'),
        ('Mammalian Lentiviral', 'Mammalian Lentiviral'),
        ('Mammalian Integrating', 'Mammalian Integrating')], default='')
    plasmid_type_other = StringField('Other')
    bac_selection = SelectField('Bacterial selection', choices=[
        ('', 'Select one'),
        ('None', 'None'), ('Amp', 'Amp/Carb'), ('Cm', 'Cm'), ('Kn', 'Kan'),
        ('Neo', 'Neo'), ('Phleo', 'Phleo'), ('Spec', 'Spec'), ('Tet', 'Tet')], default='')
    bac_sel_other = StringField('Other')
    yeast_mamm_selection = SelectField('Yeast/Mammalian selection', choices=[
        ('', 'Select one'), ('NA', 'Not applicable'),
        ('TRP', 'TRP'), ('HIS', 'HIS'), ('URA', 'URA'), ('LEU', 'LEU'),
        ('KAN', 'KAN'), ('NAT', 'NAT'), ('yHYG', 'HYG (Yeast)'),
        ('Blasticidin', 'Blasticidin'), ('mHYG', 'HYG (Mammalian)'),
        ('Neo', 'Neo'), ('Puro', 'Puro'), ('Zeo', 'Zeo')], default='')
    yeast_mamm_sel_other = StringField('Other')
    promoter = SelectField('Promoter', choices=[
        ('', 'Select one'),
        ('pGAL', 'pGAL'), ('pTDH3', 'pTDH3/pGPD'), ('pZ4EV', 'pZ4EV'),
        ('pZ3EV', 'pZ3EV'), ('pTET', 'pTET'), ('pCUP', 'pCUP'),
        ('pMET', 'pMET'), ('CMV', 'CMV'), ('CAG', 'CAG'), ('MSCV', 'MSCV'),
        ('Psyn1', 'Psyn1'), ('Psyn135', 'Psyn135'), ('PT7', 'PT7'),
        ('PR', 'PR'), ('Plac', 'Plac'), ('Ptac', 'Ptac'), ('Para', 'Para')], default='')
    promoter_other = StringField('Other')
    fusion = SelectField('Fusion', choices=[
        ('', 'Select one'),
        ('GFP', '(e)GFP'), ('YFP', '(e)YFP/Citrine'), ('RFP', 'RFP/mCherry'),
        ('CFP', '(e)CFP'), ('mTurquoise2', 'mTurquoise2'), ('sfGFP', 'sfGFP'),
        ('sfYFP', 'sfYFP'), ('mNeongreen', 'mNeongreen'),
        ('BFP', 'BFP/TagBFP(2)'), ('mEOS', 'mEOS variant'), ('Myc', 'Myc'),
        ('HA', 'HA'), ('FLAG', 'FLAG'), ('6His', '6His'), ('10His', '10His'),
        ('MBP', 'MBP'), ('GST', 'GST'), ('SUMO', 'SUMO'), ('MalE', 'MalE'),
        ('SBP', 'SBP'), ('BiFC', 'BiFC fragment'), ('Gal4', 'Y2H (Gal4)'),
        ('Ubi', 'Y2H (Ubi)')],
                         default='')
    fusion_other = StringField('Other')
    download_map = SubmitField('Download Plasmid Map')
    plasmid_map = FileField("Upload new plasmid map (.gb preferred)")
    sequenced = BooleanField('Insert sequenced?')
    download_data = SubmitField('Download Data File')
    data_file = FileField('Upload New Data File (<25 MB)')
    notes = TextAreaField('Notes')
    parents = StringField('Parent pVD #(s)')
    submit = SubmitField('Submit changes')


class StrainGenotype(Form):
    genotype = StringField('Genotype', validators=[Length(max=50)])


class SearchStrainsForm(FlaskForm):
    gate = RadioField('', choices=[
        ('OR', 'ANY of these fields (ex. entered by Vlad OR with deltaget3 in genotype)'),
        ('AND', 'ALL of these fields (ex. entered by Vlad AND with deltaget3 in genotype)')],
                      default='OR', validators=[DataRequired()])
    VDY_number = StringField('VDY number')
    VDY_range_end = StringField('VDY range end')
    other_names = StringField('Other name(s)')
    start_date = DateField('Date range start, format YYYY-MM-DD')
    end_date = DateField('Date range end, format YYYY-MM-DD')
    origin = StringField('Lab of Origin')
    creator = StringField('Creator')
    parent = StringField('Parent Strain')
    strain_background = StringField('Strain Background and/or Mating Type')
    notebook_ref = StringField('Notebook Reference')
    marker = StringField('Selectable Marker')
    plasmid = StringField('Replicating Plasmid')
    plasmid_selexn = StringField('Plasmid Selection')
    notes = TextAreaField('Notes')
    genotype_list = FieldList(FormField(StrainGenotype), min_entries=10)
    genotype_gate = RadioField('', choices=[
        ('OR', 'ANY of the following loci'),
        ('AND', 'ALL of the following loci')],
                      default='OR', validators=[DataRequired()])
    submit = SubmitField('Search')
    show_all = SubmitField('Show All Strains')
    all_by_me = SubmitField('Show All Strains I Entered')


class NewStrainForm(FlaskForm):
    new_other_names = StringField('Other name(s)')
    new_origin = StringField('Lab of Origin')
    new_creator = StringField('Creator')
    new_strain_background = StringField('Strain Background and/or Mating Type')
    new_notebook_ref = StringField('Notebook Reference')
    new_marker = StringField('Selectable Marker')
    new_plasmid = StringField('Replicating Plasmid')
    new_plasmid_selexn = StringField('Plasmid Selection')
    new_notes = TextAreaField('Notes')
    parent_strain = StringField('Parent Strain')
    new_genotype_list = FieldList(FormField(StrainGenotype), min_entries=10)
    validation = MultiCheckboxField(
        'Validation Method(s)',
        choices=((0, 'Not Validated'), (1, 'Colony PCR'), (2, 'Western Blot'),
                 (3, 'Sequencing'), (4, 'Microscopy'),
                 (5, 'Other (see Notes)')),
        default=[0])
    data_file = FileField('Upload image with relevant data')
    new_submit = SubmitField('Search')

    def to_temp_record(self, data_fname):
        """Create entry in TempStrain table and return id."""
        # handle empty creator string
        if not self.new_creator.data:
            self.new_creator.data = current_user.username
        # create temp record in temp strain table
        new_record = TempStrain(
            creator_id=current_user.id,
            creator_str=self.new_creator.data,
            other_names=self.new_other_names.data,
            strain_background=self.new_strain_background.data,
            notebook_ref=self.new_notebook_ref.data,
            marker=self.new_marker.data,
            plasmid=self.new_plasmid.data,
            plasmid_selexn=self.new_plasmid_selexn.data,
            validation=self.validation.data,
            image_filename=data_fname,
            notes=self.new_notes.data,
            parent=self.parent_strain.data)
        db.session.add(new_record)
        db.session.commit()
        # add locus details from genotype fields to temp genotype table
        for locus_ref, locus_data in self.genotype_list.data:
            temp_gt = TempStrainGenotype(temp_strain_id=new_record.temp_id,
                                         locus_info=locus_data)
            db.session.add(temp_gt)
            db.session.commit()
        return new_record.temp_id


class DownloadRecords(FlaskForm):
    download = SubmitField("Download to CSV")
