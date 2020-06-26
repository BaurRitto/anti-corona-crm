# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app import constants as c
from app.main.forms import UploadDataForm
from flask_wtf import FlaskForm
from flask_babelex import _
from wtforms.validators import DataRequired
from wtforms import TextField, DateField, SelectField, RadioField, BooleanField, SelectMultipleField, IntegerField
from wtforms.fields import html5 as h5fields
from wtforms.widgets import html5 as h5widgets

class PatientForm(FlaskForm):
    travel_type = SelectField('Travel Type', id='travel_type', validators=[DataRequired()])

    # Flight Travel
    flight_arrival_date = SelectField('Flight Arrival Date', id='flight_arrival_date', validators=[DataRequired()])
    flight_code_id = SelectField('Flight Code', id='flight_code_id', validators=[DataRequired()])
    flight_seat = TextField('Flight Seat', id='flight_seat')

    # Train Travel
    train_departure_date = DateField('Train Departure Date', validators=[DataRequired()])
    train_arrival_date = DateField('Train Arrival Date')
    train_id = SelectField('Train', choices=[], validators=[DataRequired()])
    train_wagon = TextField('Train Wagon')
    train_seat = TextField('Train Seat')

    # Travel by auto, foot, sea
    arrival_date = DateField('Arrival Date', validators=[DataRequired()])
    auto_border_id = SelectField('By Auto Border', validators=[DataRequired()])
    foot_border_id = SelectField('By Foot Border', id='foot_border_id', validators=[DataRequired()])
    sea_border_id = SelectField('By Sea Border', validators=[DataRequired()])

    # Blockpost Travel
    blockpost_region_id = SelectField('Blockpost Region', validators=[DataRequired()])    

    first_name = TextField('First Name', validators=[DataRequired()])
    second_name = TextField('Second Name', validators=[DataRequired()])
    patronymic_name = TextField('Patronymic Name')

    gender = RadioField('Gender', choices=[(0, _("Мужчина")), (1, _("Женщина")), (-1, _("Неизвестно"))], 
                                                                            default = -1, validators=[DataRequired()])
    dob = DateField('DoB', validators=[DataRequired()])
    iin = TextField('IIN')

    citizenship_id = SelectField('Citizenship', validators=[DataRequired()])
    pass_num = TextField('Pass No.', id='pass_num')
    country_of_residence_id = SelectField('Residence Country', validators=[DataRequired()])

    home_address_country_id = SelectField('Home Address Country', validators=[DataRequired()])
    home_address_state = TextField('Home State')
    home_address_county = TextField('Home County')
    home_address_city = TextField('Home City')
    home_address_street = TextField('Home Street')
    home_address_house = TextField('Home House')
    home_address_flat = TextField('Home Flat')
    home_address_building = TextField('Home Building')
    home_address_location_type_id = SelectField('Home Address Location Type Id', validators=[DataRequired()])

    visited_country_id = SelectField('Visited Country', validators=[DataRequired()])
    visited_from_date = DateField('Visit From Date')
    visited_to_date = DateField('Visit To Date')
   
    region_id = SelectField('Region', id='region', validators=[DataRequired()])

    job = TextField('Job')
    job_position = TextField('Job Position')
    job_category_id = SelectField('Job Category')

    job_address_country_id = SelectField('Job Address Country')
    job_address_state = TextField('Job State')
    job_address_county = TextField('Job County')
    job_address_city = TextField('Job City')
    job_address_street = TextField('Job Street')
    job_address_house = TextField('Job House')
    job_address_flat = TextField('Job Flat')
    job_address_building = TextField('Job Building')

    telephone = TextField('Telephone', id='telephone')
    email = TextField('EMail', id='email')

    hospital_region_id = SelectField('Hospital Region' , validators=[DataRequired()])
    hospital_type_id = SelectField('Hospital Type' , validators=[DataRequired()])
    hospital_id = SelectField('Hospital', choices = [], validators=[DataRequired()])

    is_home_end = DateField("Duration of Home Quarantine")

    # patient_states = SelectField(id='patient_states')
    is_found = RadioField("Is Found", choices=[(1, _("Да")),(0, _("Нет"))], default=0, validators=[DataRequired()])
    is_found_date = DateField("Is Found Date")

    is_transit = RadioField("Is Transit", choices=[(1, _("Да")),(0, _("Нет"))], default=0, validators=[DataRequired()])
    patient_status = SelectField('Patient Status', id='patient_status' , validators=[DataRequired()])

    state_infec_type = SelectField(choices=c.state_infec_types)
    state_infec_illness_symptoms = SelectField(choices=c.illness_symptoms)
    state_infec_illness_severity = SelectField(choices=c.illness_severity)

    state_dead_reason = SelectField(choices=c.death_reasons)

    # is_contacted = RadioField("Is Contacted", id="is_contacted", choices=[(1, _("Да")),(0, _("Нет"))], default=0, validators=[DataRequired()])


class UpdateProfileForm(PatientForm):
    is_found = BooleanField(id="is_found")
    is_infected = BooleanField(id="is_infected")
    # is_contacted = BooleanField(id="is_contacted")
    in_hospital = BooleanField(id="in_hospital")
    is_home = BooleanField(id="is_home")
    citizenship = TextField('Citizenship', id='citizenship', validators=[DataRequired()])
    flight_code_id = SelectField('Flight Code', id='flight_code_id')

    state = SelectField('State' , validators=[DataRequired()])
    stateComment = TextField('State Comment', id='stateComment')
    stateDetectionDate = DateField('State Detection Date')


class AddFlightFromExcel(UploadDataForm):
    flights_id = SelectField('Flights ID', id='flights_id' , validators=[DataRequired()])

class ContactedPatientsSearchForm(FlaskForm):
    full_name = TextField("Full Name")
    region_id = SelectField("Region ID")
    is_found = SelectField("Is Found", choices=[(-1, _("Неважно")), (1, _("Да")), (0, _("Нет"))], default=-1)
    is_added_in_2_hours = SelectField("Is Added in 2 Hours", choices=[(-1, _("Неважно")), (1, _("Да")), (0, _("Нет"))], default=-1)
    is_infected = SelectField("Is Infected", choices=[(-1, _("Неважно")), (1, _("Да")), (0, _("Нет"))], default=-1)
    contact_type = SelectField('Contact Type', choices=[(-1, _("Неважно")), (1, _("(ПК) Потенциальный Контакт")), 
                                                        (0, _("(БК) Близкий Контакт"))], validators=[DataRequired()])

class PatientsSearchForm(FlaskForm):
    region_id = SelectField()
    address = TextField()
    
    travel_type = SelectField()
    job_category_id = SelectField()

    probably_duplicate = BooleanField()
    contacted = SelectField("Contacted or with Contacts",
                            choices=[(-1, _("Все")), ("contacted", _("Контактный")), ("with_contacts", _("С Контактами")),
                                    ("contacted_close", _("Контактный (БК)")), ("contacted_potential", _("Контактный (ПК)"))], default=-1)


    is_currently_infected = SelectField("Is Currently Infected",
                            choices=[(-1, _("Все")), (1, _("Да")), (0, _("Нет"))], default=-1)
    # is_infected = SelectField("Is Infected", choices=[(-1, _("Все")), (1, _("Да")), (0, _("Нет"))], default=-1)
    is_found = SelectField("Is Found", choices=[(-1, _("Все")), (1, _("Да")), (0, _("Нет"))], default=-1)

    patient_status = SelectField(choices=[(-1, _("Все Статусы")),
                                          ("in_hospital", _("Госпитализирован")),
                                          ("not_in_hospital", _("Не госпитализирован")),
                                          ("is_home_quarantine", _("Домашний Карантин")),
                                          ("is_transit", _("Транзит"))])

    is_iin_fail = SelectField(choices=[(-1, _("Все ИИНы")),
                                       ("is_iin_empty", _("ИИН Пустой")),
                                       ("is_iin_invalid", _("ИИН Неправильный")),
                                       ("is_iin_valid", _("ИИН Правильный"))])

    #Date Range
    date_range_start = DateField()
    date_range_end = DateField()

    #States with Dates
    patient_state = SelectField('State', choices=[(-1, _("Все Статусы"))] + c.states)
    state_date_range_start = DateField()
    state_date_range_end = DateField()
    state_count_min = h5fields.IntegerField("State Count Min", widget=h5widgets.NumberInput(min=0, max=100, step=1))
    state_count_max = h5fields.IntegerField("State Count Max", widget=h5widgets.NumberInput(min=0, max=100, step=1))

    #States - Infected
    state_infec_type = SelectField(choices=[c.all_types_none] + c.state_infec_types)
    state_infec_illness_symptoms = SelectField(choices=[c.all_types_none] + c.illness_symptoms)
    state_infec_illness_severity = SelectField(choices=[c.all_types_none] + c.illness_severity)    

    #States - Dead
    state_dead_reason = SelectField(choices=[c.all_types_none] + c.death_reasons)

    # Flight Travel
    flight_arrival_date = SelectField('Flight Arrival Date', id='flight_arrival_date')
    flight_code_id = SelectField('Flight Code', id='flight_code_id')

    # Train Travel
    train_departure_date = DateField('Train Departure Date')
    train_arrival_date = DateField('Train Arrival Date')
    train_id = SelectField('Train', choices=[])

    travel_departure_outer = SelectField(choices=[("all_travel", _("Все Рейсы")),
                                                  ("outer_travel", _("Внешние Рейсы")),
                                                  ("domestic_travel", _("Внутренние Рейсы"))], default="all_travel")

    # Travel by auto, foot, sea
    arrival_date = DateField('Arrival Date')
    auto_border_id = SelectField('By Auto Border')
    foot_border_id = SelectField('By Foot Border')
    sea_border_id = SelectField('By Sea Border')

    # Blockpost Travel
    blockpost_region_id = SelectField('Blockpost Region')    

    first_name = TextField('First Name')
    second_name = TextField('Second Name')
    patronymic_name = TextField('Patronymic Name')

    iin = TextField(id='iin')
    pass_num = TextField()
    telephone = TextField(id='telephone')

    home_address_location_type_id = SelectField('Home Address Location Type Id', validators=[DataRequired()])

class SelectContactedForm(FlaskForm):
    contact_type = SelectField('Contact Type', choices=[(1, _("(ПК) Потенциальный Контакт")), (0, _("(БК) Близкий Контакт"))],
                                                validators=[DataRequired()])