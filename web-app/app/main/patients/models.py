# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, JSON, DateTime

from app import db
from app import constants as c
from app.login.models import User
from app.main.models import Country, Address, VisitedCountry
from app.login.util import hash_pass

class State(db.Model):
    """
    State class represents Patient state:
    * infected
    * dead
    * healthy
    """

    __tablename__ = 'State'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class PatientState(db.Model):
    """
    PatientState represents many-to-many relationship between Patient and State tables.
    Table includes:
    * created_at: creation datetime
    * detection_date: datetime of detection
    * comment: comment on state
    """
    __tablename__ = 'PatientState'

    id = Column(Integer, primary_key=True)
    state_id = Column(Integer, nullable=False)
    patient_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    detection_date = Column(DateTime, default=datetime.datetime.utcnow)
    comment = Column(String, nullable=True)

class Patient(db.Model):

    __tablename__ = 'Patient'

    id = Column(Integer, primary_key=True)
    attrs = Column(JSON, unique=False)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('User.id'))
    created_by = db.relationship('User')
    travel_type_id = Column(Integer, ForeignKey('TravelType.id'), nullable=True, default=None)
    travel_type = db.relationship('TravelType')
    travel_id = Column(Integer, nullable=True, default=None, unique=False)
    first_name = Column(String, unique=False)
    second_name = Column(String, unique=False)
    patronymic_name = Column(String, unique=False, nullable=True)

    # False - male, True - female, None - unknown
    gender = Column(Boolean, nullable=True, default=None)
    dob = Column(Date, nullable=False)
    iin = Column(String, nullable=True, default=None)
    citizenship_id = Column(Integer, ForeignKey('Country.id'))
    citizenship = db.relationship('Country', foreign_keys=[citizenship_id])
    pass_num = Column(String, unique=False, nullable=True, default=None)
    country_of_residence_id = Column(Integer, ForeignKey('Country.id'), nullable=True)
    country_of_residence = db.relationship('Country', foreign_keys=[country_of_residence_id])
    home_address_id = Column(Integer, ForeignKey('Address.id'), nullable=False)
    home_address = db.relationship('Address', 
                                    foreign_keys=[home_address_id], 
                                    cascade="all,delete", 
                                    backref="Patient")
    telephone = Column(String, nullable=True, default=None)
    email = Column(String, nullable=True, default=None)
    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')
    hospital_id = Column(Integer, ForeignKey('Hospital.id'), nullable=True, default=None)
    hospital = db.relationship('Hospital')
    job = Column(String, nullable=True, default=None)
    job_position = Column(String, nullable=True, default=None)
    job_address_id = Column(Integer, ForeignKey('Address.id'), nullable=True, default=None)
    job_address = db.relationship('Address', 
                                    foreign_keys=[job_address_id],
                                    cascade="all, delete-orphan",
                                    single_parent=True)

    # DEPRECATED
    status_id = Column(Integer, ForeignKey('PatientStatus.id'))
    status = db.relationship('PatientStatus')
    is_contacted_person = Column(Boolean, unique=False)
    is_contacted = Column(Boolean, unique=False, default=False)

    # infected, dead, healthy
    # states = db.relationship("State", secondary=lambda: PatientState.__table__,
    #                          backref=db.backref("patients"))
    @property
    def states(self):
        results = PatientState.query.filter_by(patient_id=self.id).all()
        results = sorted(results, key=lambda k: k.detection_date, reverse=True)
        for i in range(len(results)):
            results[i].name = State.query.filter_by(id=results[i].state_id).first().name
            results[i].formatted_detection_date = datetime.datetime.strftime(results[i].detection_date, "%d.%m.%Y")
            results[i].formatted_comment = results[i].comment
            if results[i].comment is None:
                results[i].formatted_comment = "Нет деталей"
        return results
    
    def addState(self, state: PatientState):
        if self.id is None:
            return
        state.patient_id = self.id
        db.session.add(state)
        db.session.commit()
        return state

    # is_found = Column(Boolean, unique=False, default=False)
    @property
    def is_found(self):
        state = State.query.filter_by(name=c.state_found).first()
        found = PatientState.query.filter_by(patient_id=self.id).filter_by(state_id=state.id).first()
        if found:
            return True
        return False
    
    @is_found.setter
    def is_found(self, value):
        if value == True and self.id is not None:
            state = State.query.filter_by(name=c.state_found).first()
            patientState = PatientState(
                state_id=state.id,
                patient_id=self.id
            )
            db.session.add(patientState)
            db.session.commit()

    # is_infected = Column(Boolean, unique=False, default=False)
    @property
    def is_infected(self):
        state = State.query.filter_by(name=c.state_infec).first()
        infec = PatientState.query.filter_by(patient_id=self.id).filter_by(state_id=state.id).first()
        if infec:
            return True
        return False
    
    @is_infected.setter
    def is_infected(self, value):
        if value == True and self.id is not None:
            state = State.query.filter_by(name=c.state_infec).first()
            patientState = PatientState(
                state_id=state.id,
                patient_id=self.id
            )
            db.session.add(patientState)
            db.session.commit()
    

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return "{} {} {}".format(str(self.second_name), str(self.first_name), str(self.patronymic_name))

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        color = "green"
        if self.is_infected == True:	
            color = "red"
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {"type": "Point", "coordinates": [self.home_address.lat, self.home_address.lng]},
            "properties": {
                    "balloonContent": "идет загрузка...",
                    "clusterCaption": "идет загрузка...",
                    # "hintContent": "Текст подсказки"
            },
            "options": {
                "preset": "islands#icon",
                "iconColor": color
            }
        }

    def get_created_date(self):
        sql = "select * from logging.t_history WHERE tabname='{}' \
                AND new_val->>'id'='{}' AND operation='INSERT';".format(self.__tablename__, self.id)
        result = db.engine.execute(sql)
        created_date = result.fetchone()[1]

        return created_date

class ContactedPersons(db.Model):
    __tablename__ = 'ContactedPersons'

    id = Column(Integer, primary_key=True)
    infected_patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    infected_patient = db.relationship('Patient', foreign_keys=[infected_patient_id],
                                       backref=db.backref('infected_patient', passive_deletes=True))
    contacted_patient_id = Column(Integer, ForeignKey('Patient.id'))
    contacted_patient = db.relationship('Patient', foreign_keys=[contacted_patient_id])

    attrs = Column(JSON, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)

    @property
    def created_date(self):
        sql = "select * from logging.t_history WHERE tabname='ContactedPersons' \
                AND new_val->>'id'='{}' AND operation='INSERT';".format(self.id)
        result = db.engine.execute(sql)
        created_date = result.fetchone()[1]

        return created_date

    def added_in_n_hours(self, hours = 2):
        infected_created_date = self.infected_patient.get_created_date()

        return self.created_date - infected_created_date < datetime.timedelta(hours=hours)

class PatientStatus(db.Model):
    """
    DEPRECATED
    PatientStatus class for representing Patient's current status:
    1 | no_status   | Нет Статуса
    2 | in_hospital | Госпитализирован
    3 | is_home     | Домашний Карантин
    4 | is_transit  | Транзит
    """

    __tablename__ = 'PatientStatus'

    id = Column(Integer, primary_key=True)
    value = Column(String, unique=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)
