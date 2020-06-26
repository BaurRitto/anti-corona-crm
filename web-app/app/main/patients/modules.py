from flask import request, Response
import math
from app.main.modules import TableModule

from app.main.patients.models import Patient, ContactedPersons, PatientStatus, PatientState, State
from app.main.models import TravelType, VariousTravel, BlockpostTravel, Address, Country, Region, JobCategory, BorderControl, AddressLocationType
from app.main.flights_trains.models import FlightTravel, TrainTravel, FlightCode, Train
from app.login.models import User

from collections import OrderedDict
from app.main.util import parse_date, yes_no_html, yes_no, custom_yes_no
from app.main.patients.util import measure_patient_similarity

from sqlalchemy import func, cast, JSON, exc, text
import sqlalchemy

from flask_babelex import _
from app import constants as c

import pandas as pd
import io
import urllib

class ContactedPatientsTableModule(TableModule):
    def __init__(self, request, q, search_form, header_button = None, page = 1, per_page = 5, download_xls_access = False):
        table_head = OrderedDict()
        table_head[_("ФИО")] = ["second_name"]
        table_head[_("БК или ПК")] = ["is_potential_contact"]
        table_head[_("Телефон")] = ["telephone"]
        table_head[_("Тип Въезда")] = ["travel_type_id"]
        table_head[_("Регион")] = []
        table_head[_("Найден")] = ["is_found"]
        table_head[_("В Больнице")] = []
        table_head[_("Инфицирован")] = ["is_infected"]
        table_head[_("Удалить Связь")] = []
        table_head[_("Добавлен за 2 часа")] = []
        table_head[_("Дата Создания Пациента")] = ["created_date"]

        is_downloadable_xls = download_xls_access

        super().__init__(request, q, table_head, header_button, search_form, sort_param="contacted_patient",
                            is_downloadable_xls=is_downloadable_xls)

    def download_xls(self):
        if not self.is_downloadable_xls:
            return None

        data = []
        for row in self.q.all():
            patient = row.contacted_patient

            is_infected = yes_no(patient.is_infected)
            is_found = yes_no(patient.is_found)

            data.append([patient.id, str(patient), patient.iin, str(patient.home_address),
                        patient.telephone, is_found, is_infected ])

        data = pd.DataFrame(data, columns=[_("ID"), _("ФИО"), _("ИИН"), _("Домашний Адрес"), _("Телефон"),
                                           _("Найден"), _("Инфицирован") ])

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        data.to_excel(writer, index=False)

        def get_col_widths(df):
            widths = []
            for col in df.columns:
                col_data_width = max(df[col].map(str).map(len).max(), len(col))
                col_data_width *= 1.2

                widths.append(col_data_width)
            
            return widths

        for i, width in enumerate(get_col_widths(data)):
            writer.sheets['Sheet1'].set_column(i, i, width)

        writer.save()
        xlsx_data = output.getvalue()

        region_id = int(request.args.get("region_id", -1))
        region_name = c.all_regions
        
        region_query = Region.query.filter_by(id = region_id)
        if region_query.count():
            region_name = region_query.first().name

        filename_xls = "{}_{}".format(_("пациенты"), region_name)

        date_range_start = request.args.get("date_range_start", None)
        if date_range_start:
            filename_xls = "{}_{}".format(filename_xls, date_range_start)

        date_range_end = request.args.get("date_range_end", None)
        if date_range_end:
            filename_xls = "{}_{}".format(filename_xls, date_range_end)

        filename_xls = "{}.xls".format(filename_xls)
        
        response = Response(xlsx_data, mimetype="application/vnd.ms-excel")
        response.headers["Content-Disposition"] = \
            "attachment;" \
            "filename*=UTF-8''{}".format(urllib.parse.quote(filename_xls.encode('utf-8')))

        return response

    def search_table(self):
        full_name_value = self.request.args.get("full_name", None)
        if full_name_value:
            self.q = self.q.filter(func.lower(func.concat(Patient.second_name, ' ', Patient.first_name, ' ', 
                                    Patient.patronymic_name)).contains(full_name_value.lower()))
            
            self.search_form.full_name.default = full_name_value

        region_id = self.request.args.get("region_id", -1)
        if region_id:
            region_id = int(region_id)
            if region_id != -1:
                self.q = self.q.filter(Patient.region_id == region_id)
                self.search_form.region_id.default = region_id

        is_found = self.request.args.get("is_found", "-1")
        if is_found != "-1":
            self.q = self.q.filter(Patient.is_found == bool(int(is_found)))
            self.search_form.is_found.default = is_found

        is_infected = self.request.args.get("is_infected", "-1")
        if is_infected != "-1":
            self.q = self.q.filter(Patient.is_infected == bool(int(is_infected)))
            self.search_form.is_infected.default = is_infected        

        is_added_in_2_hours = self.request.args.get("is_added_in_2_hours", "-1")
        if is_added_in_2_hours != "-1":
            infected_patient_id = request.args['id']

            valid_ids = []
            for c in self.q.all():
                if c.added_in_n_hours() == bool(int(is_added_in_2_hours)):
                    valid_ids.append(c.id)

            self.q = self.q.filter(ContactedPersons.id.in_(valid_ids))
            self.search_form.is_added_in_2_hours.default = is_added_in_2_hours

        contact_type = self.request.args.get("contact_type", "-1")
        if contact_type != "-1":
            is_potential_contact = int(contact_type) == 1

            self.q = self.q.filter(ContactedPersons.is_potential_contact == is_potential_contact)
            self.search_form.contact_type.default = contact_type

        self.search_form.process()

    def print_entry(self, result):
        patient = result.contacted_patient

        patient_id = (patient, "/patient_profile?id={}".format(patient.id))
        potential_or_close = custom_yes_no(_("ПК"), _("БК"), result.is_potential_contact)
        telephone = patient.telephone
        travel_type = patient.travel_type
        region = patient.region

        is_found = yes_no_html(False)
        if patient.is_found:
            is_found = yes_no_html(True)

        in_hospital = yes_no_html(False)
        if patient.status and patient.status.value == c.in_hospital[0]:
            in_hospital = yes_no_html(True)

        is_infected = yes_no_html(False, invert_colors=True)
        if patient.is_infected:
            is_infected = yes_no_html(True, invert_colors=True)

        delete_contact_html = "<a href=\"/delete_contacted?contact_id={}\" class=\"btn btn-danger\">{}</a>".format(
                                result.id, _("Удалить Связь"))
        delete_contact_button = (delete_contact_html, "safe")

        is_added_in_2_hours = yes_no_html(True if result.added_in_n_hours() else False)

        created_date = patient.created_date.strftime("%d-%m-%Y %H:%M")

        return [patient_id, potential_or_close, telephone, travel_type, region, is_found, \
                in_hospital, is_infected, delete_contact_button, is_added_in_2_hours, created_date]

class AllPatientsTableModule(TableModule):
    def __init__(self, request, q, select_contacted = None, search_form = None, page = 1, per_page = 5, download_xls_access = False):
        table_head = OrderedDict()
        self.select_contacted = select_contacted

        is_downloadable_xls = download_xls_access
        header_button = [(_("Добавить Пациента"), "/add_person")]
        table_head_info = dict()

        if select_contacted:
            table_head[_("Выбрать контактных")] = []
            table_head_info[_("Выбрать контактных")] = ("checkbox", "contacted_all_checkboxes")


            infected_contacted = ContactedPersons.query.filter_by(infected_patient_id=select_contacted)
            self.infected_contacted_ids = []
            self.infected_contact_type = {}

            for c in infected_contacted:
                self.infected_contacted_ids.append(c.contacted_patient_id)
                self.infected_contact_type[c.contacted_patient_id] = c.is_potential_contact

            contacted_infected = ContactedPersons.query.filter_by(contacted_patient_id=select_contacted)
            self.contacted_infected_ids = []
            self.contacted_contact_type = {}

            for c in contacted_infected:
                self.contacted_infected_ids.append(c.infected_patient_id)
                self.contacted_contact_type[c.infected_patient_id] = c.is_potential_contact

            is_downloadable_xls = False
            header_button = [(_("Добавить Контактных"), "#", "add_contacted", "disabled data-toggle=modal data-target=#addContactedModal")]

        table_head[_("ФИО")] = ["second_name"]
        table_head[_("ИИН")] = ["iin"]
        table_head[_("Тип Въезда")] = ["travel_type_id"]
        table_head[_("Регион")] = []
        table_head[_("Найден")] = ["is_found"]
        table_head[_("Госпитализирован")] = []
        table_head[_("Сейчас Инфицирован")] = ["is_infected"]
        table_head[_("Контактов (найдено/всего)")] = []
        table_head[_("Время Добавления")] = ["created_date"]

        super().__init__(request, q, table_head, header_button, search_form, is_downloadable_xls=is_downloadable_xls, 
                        table_head_info = table_head_info)

    def preprocess_entries(self, entries):
        if "probably_duplicate" in self.request.args:
            for i, entry in zip(range(len(entries)), entries):
                if entry.get("class", None) != "duplicateRow":
                    for a in range(i + 1, len(entries)):
                        if measure_patient_similarity(entry["data"][0][0], entries[a]["data"][0][0]) >= 0.90:
                            entry["class"] = "duplicateRow"
                            entries[a]["class"] = "duplicateRow"

            self.search_form.probably_duplicate.checked = True

        return entries

    def search_table(self):    
        region_id = self.request.args.get("region_id", -1)
        if region_id:
            region_id = int(region_id)

            if region_id != -1:
                self.q = self.q.filter(Patient.region_id == region_id)
                self.search_form.region_id.default = region_id
                
                self.search_params.append((_("Регион"), Region.query.filter_by(id = region_id).first().name))

        filt = dict()

        job_category_id = self.request.args.get("job_category_id", "-1")
        if job_category_id != "-1":
            job_category_disp_name = _("Неизвестно")
            if job_category_id == "None":
                job_category_id = None
            else:
                job_category_id = int(job_category_id)
                job_category_disp_name = JobCategory.query.filter_by(id = job_category_id).first().name

            self.search_params.append((_("Категория Работы"), job_category_disp_name))
            self.q = self.q.filter(Patient.job_category_id == job_category_id)
            self.search_form.job_category_id.default = job_category_id
        
        is_found = self.request.args.get("is_found", "-1")
        if is_found != "-1":
            filt["is_found"] = is_found == "1"
            self.search_form.is_found.default = is_found

            self.search_params.append((_("Найден"), _("Да") if is_found == "1" else _("Нет")))

        is_currently_infected = self.request.args.get("is_currently_infected", "-1")
        if is_currently_infected != "-1":
            filt["is_infected"] = is_currently_infected == "1"
            self.search_form.is_currently_infected.default = is_currently_infected

            self.search_params.append((_("Инфицирован"), _("Да") if filt["is_infected"] else _("Нет")))

        def name_search(param, param_str, q, param_disp_name):
            if param_str in request.args:
                req_str = request.args[param_str]

                if req_str:
                    q = q.filter(func.lower(param).contains(req_str.lower()))
                    param = getattr(self.search_form, param_str, None)
                    if param:
                        setattr(param, 'default', req_str)
                        
                        self.search_params.append((param_disp_name, req_str))
            
            return q

        self.q = name_search(Patient.first_name, "first_name", self.q, _("Имя"))
        self.q = name_search(Patient.second_name, "second_name", self.q, _("Фамилия"))
        self.q = name_search(Patient.patronymic_name, "patronymic_name", self.q, _("Отчество"))

        iin = request.args.get("iin", "")
        if iin:
            self.q = self.q.filter(Patient.iin.contains(iin))
            self.search_form.iin.default = iin
            
            self.search_params.append((_("ИИН"), iin))

        pass_num = request.args.get("pass_num", "")
        if pass_num:
            self.q = self.q.filter(Patient.pass_num.contains(pass_num))
            self.search_form.pass_num.default = pass_num
            
            self.search_params.append((_("Номер Паспорта"), pass_num))

        travel_type = request.args.get("travel_type", c.all_travel_types[0])
        if travel_type and travel_type != c.all_travel_types[0]:
            try:
                travel_type_query = TravelType.query.filter_by(value=travel_type).first()
                travel_type_id = travel_type_query.id
            except (exc.SQLAlchemyError, AttributeError):
                raise exc.SQLAlchemyError("Travel Type Error - {}".format(travel_type))

            if travel_type_id:
                filt["travel_type_id"] = travel_type_id
                self.search_form.travel_type.default = travel_type

            self.search_params.append((_("Тип Въезда"), travel_type_query.name))

        # Created_date range
        date_range_start = request.args.get("date_range_start", None)
        
        if date_range_start:
            date_range_start = parse_date(date_range_start)
            self.q = self.q.filter(Patient.created_date >= date_range_start)
            self.search_form.date_range_start.default = date_range_start
            
            self.search_params.append((_("Дата Создания (Начало)"), date_range_start.strftime('%Y-%m-%d')))

        date_range_end = request.args.get("date_range_end", None)
        
        if date_range_end:
            date_range_end = parse_date(date_range_end)
            self.q = self.q.filter(Patient.created_date <= date_range_end)
            self.search_form.date_range_end.default = date_range_end

            self.search_params.append((_("Дата Создания (Конец)"), date_range_end.strftime('%Y-%m-%d')))

        self.q = self.q.filter_by(**filt)

        # State search
        patient_state = self.request.args.get("patient_state", "-1")
        if patient_state != "-1":
            # State Filter
            patient_state_val = State.query.filter_by(value=patient_state).first()
            patient_state_id = patient_state_val.id

            patient_state_disp_name = patient_state_val.name

            self.q = self.q.join(PatientState, PatientState.patient_id == Patient.id)
            self.q = self.q.filter(PatientState.state_id == patient_state_id)            

            self.search_form.patient_state.default = patient_state

            # State Date
            # State Date Start
            state_date_range_start = request.args.get("state_date_range_start", None)
            
            if state_date_range_start:
                state_date_range_start = parse_date(state_date_range_start)
                self.q = self.q.filter(PatientState.detection_date >= state_date_range_start)
                self.search_form.state_date_range_start.default = state_date_range_start

                patient_state_disp_name = "{} {}".format(patient_state_disp_name, state_date_range_start.strftime('%Y-%m-%d'))

            # State Date End
            state_date_range_end = request.args.get("state_date_range_end", None)
            
            if state_date_range_end:
                state_date_range_end = parse_date(state_date_range_end)
                self.q = self.q.filter(PatientState.detection_date <= state_date_range_end)
                self.search_form.state_date_range_end.default = state_date_range_end

                patient_state_disp_name = "{}:{}".format(patient_state_disp_name, state_date_range_end.strftime('%Y-%m-%d'))

            self.search_params.append((_("Статус Пациента"), patient_state_disp_name))

            # State Count
            # State Count Min
            state_count_min = request.args.get("state_count_min", None)

            if state_count_min:
                self.q = self.q.having(func.count(PatientState.id) >= state_count_min)
                self.search_form.state_count_min.default = state_count_min

                self.search_params.append((_("Минимум Статусов"), state_count_min))

            # State Count Max
            state_count_max = request.args.get("state_count_max", None)

            if state_count_max:
                self.q = self.q.having(func.count(PatientState.id) <= state_count_max)
                self.search_form.state_count_max.default = state_count_max

                self.search_params.append((_("Максимум Статусов"), state_count_max))

            # State Infec
            if patient_state_val.value == c.state_infec[0]:
                state_infec_type = request.args.get("state_infec_type", "None")
                if state_infec_type != "None":
                    param = "state_infec_type"
                    self.q = self.q.filter(text("CAST(\"PatientState\".attrs ->> '{}' AS VARCHAR) = '{}'".format(param, state_infec_type)))

                    self.search_form.state_infec_type.default = state_infec_type

                    self.search_params.append((_("Инфицирован - Тип"), dict(c.state_infec_types)[state_infec_type]))

                state_infec_illness_symptoms = request.args.get("state_infec_illness_symptoms", "None")
                if state_infec_illness_symptoms != "None":
                    param = "state_infec_illness_symptoms"
                    self.q = self.q.filter(text("CAST(\"PatientState\".attrs ->> '{}' AS VARCHAR) = '{}'".format(param, state_infec_illness_symptoms)))

                    self.search_form.state_infec_illness_symptoms.default = state_infec_illness_symptoms

                    self.search_params.append((_("Инфицирован - Симптомы"), dict(c.illness_symptoms)[state_infec_illness_symptoms]))

                state_infec_illness_severity = request.args.get("state_infec_illness_severity", "None")
                if state_infec_illness_severity != "None":
                    param = "state_infec_illness_severity"
                    self.q = self.q.filter(text("CAST(\"PatientState\".attrs ->> '{}' AS VARCHAR) = '{}'".format(param, state_infec_illness_severity)))

                    self.search_form.state_infec_illness_severity.default = state_infec_illness_severity

                    self.search_params.append((_("Инфицирован - Тяжесть Болезни"), dict(c.illness_severity)[state_infec_illness_severity]))

            # State Dead
            if patient_state_val.value == c.state_dead[0]:
                state_dead_reason = request.args.get("state_dead_reason", "None")
                if state_dead_reason != "None":
                    param = "state_dead_reason"
                    self.q = self.q.filter(text("CAST(\"PatientState\".attrs ->> '{}' AS VARCHAR) = '{}'".format(param, state_dead_reason)))

                    self.search_form.state_dead_reason.default = state_dead_reason

                    self.search_params.append((_("Умер - Причина Смерти"), dict(c.death_reasons)[state_dead_reason]))                

            self.q = self.q.group_by(Patient.id)

        # Is contacted
        contacted = self.request.args.get("contacted", "-1")
        if contacted != "-1":
            contacted_disp_name = None
            if contacted == "contacted":
                self.q = self.q.join(ContactedPersons, ContactedPersons.contacted_patient_id == Patient.id)
                self.q = self.q.group_by(Patient.id)

                contacted_disp_name = _("Контактный")
            elif contacted == "with_contacts":
                self.q = self.q.join(ContactedPersons, ContactedPersons.infected_patient_id == Patient.id)
                self.q = self.q.group_by(Patient.id)

                contacted_disp_name = _("С Контактами")
            elif contacted == "contacted_close":
                self.q = self.q.join(ContactedPersons, ContactedPersons.contacted_patient_id == Patient.id)
                self.q = self.q.filter(ContactedPersons.is_potential_contact == False)
                self.q = self.q.group_by(Patient.id)

                contacted_disp_name = _("Контактный (БК)")
            elif contacted == "contacted_potential":
                self.q = self.q.join(ContactedPersons, ContactedPersons.contacted_patient_id == Patient.id)
                self.q = self.q.filter(ContactedPersons.is_potential_contact == True)
                self.q = self.q.group_by(Patient.id)

                contacted_disp_name = _("Контактный (ПК)")

            self.search_form.contacted.default = contacted

            self.search_params.append((_("Контакты"), contacted_disp_name))

        is_iin_fail = request.args.get("is_iin_fail", None)
        if is_iin_fail:
            if is_iin_fail == "is_iin_empty":
                self.q = self.q.filter_by(iin = '')
                self.search_form.is_iin_fail.default = "is_iin_empty"
            elif is_iin_fail == "is_iin_invalid":
                self.q = self.q.filter(Patient.iin != '')
                self.q = self.q.filter(func.length(Patient.iin) != 12)
                self.search_form.is_iin_fail.default = "is_iin_invalid"
            elif is_iin_fail == "is_iin_valid":
                self.q = self.q.filter(func.length(Patient.iin) == 12)
                self.search_form.is_iin_fail.default = "is_iin_valid"

        address = self.request.args.get("address", None)
        if address:
            self.q = self.q.join(Address, Patient.home_address_id == Address.id)
            self.q = self.q.join(Country, Country.id == Address.country_id)
            self.q = self.q.group_by(Patient.id)

            self.q = self.q.filter(func.lower(func.concat(
                Country.name, ' ', Address.city, ' ', Address.street,
                ' ', Address.house, ' ', Address.flat)).contains(address.lower()))

            self.search_form.address.default = address

            self.search_params.append((_("Адрес"), address))

        current_country = Country.query.filter_by(code=c.current_country).first()

        home_address_location_type_id = self.request.args.get("home_address_location_type_id", "-1")
        if home_address_location_type_id != "-1":
            location_type = AddressLocationType.query.filter_by(id = home_address_location_type_id).first()
            self.q = self.q.join(Address, Patient.home_address_id == Address.id)
            self.q = self.q.group_by(Patient.id)

            self.q = self.q.filter(Address.location_type_id == home_address_location_type_id)

            self.search_form.home_address_location_type_id.default = home_address_location_type_id

            self.search_params.append((_("Село/Город"), location_type))

        if travel_type and travel_type != c.all_travel_types[0]:
            # FlightTravel
            if travel_type_query.value == c.flight_type[0]:
                self.q = self.q.join(FlightTravel)

                flight_code_id = request.args.get("flight_code_id", None)
                if flight_code_id != None:
                    self.q = self.q.filter(FlightTravel.flight_code_id == flight_code_id)

                    self.search_params.append((_("Номер Рейса"), FlightCode.query.filter_by(id = flight_code_id).first()))

                travel_in_out = request.args.get("travel_departure_outer", "all_travel")
                if travel_in_out != "all_travel":
                    self.q = self.q.join(FlightCode, FlightTravel.flight_code_id == FlightCode.id)
                    
                    if travel_in_out == "outer_travel":
                        self.q = self.q.filter(FlightCode.from_country != current_country)
                    elif travel_in_out == "domestic_travel":
                        self.q = self.q.filter(FlightCode.from_country == current_country)

                    self.search_form.travel_departure_outer.default = travel_in_out
            
            # TrainTravel
            elif travel_type_query.value == c.train_type[0]:
                self.q = self.q.join(TrainTravel)

                train_id = request.args.get("train_id", None)
                if train_id != None:
                    self.q = self.q.filter(TrainTravel.train_id == train_id)

                travel_in_out = request.args.get("travel_departure_outer", "all_travel")
                if travel_in_out != "all_travel":
                    self.q = self.q.join(Train, TrainTravel.train_id == Train.id)
                    
                    if travel_in_out == "outer_travel":
                        self.q = self.q.filter(Train.from_country != current_country)
                    elif travel_in_out == "domestic_travel":
                        self.q = self.q.filter(Train.from_country == current_country)

                    self.search_form.travel_departure_outer.default = travel_in_out

                    self.search_params.append((_("Поезд"), Train.query.filter_by(id = train_id).first()))

            # Blockpost
            elif travel_type_query.value == c.blockpost_type[0]:
                self.q = self.q.join(BlockpostTravel)

                arrival_date = request.args.get("arrival_date", None)
                if arrival_date:
                    self.q = self.q.filter(BlockpostTravel.date == arrival_date)
                    self.search_form.arrival_date.default = parse_date(arrival_date)

                blockpost_region_id = request.args.get("blockpost_region_id", "-1")
                if blockpost_region_id != "-1":
                    self.q = self.q.filter(BlockpostTravel.region_id == blockpost_region_id)
                    self.search_form.blockpost_region_id.default = blockpost_region_id

                    self.search_params.append((_("Блокпост"), Region.query.filter_by(id = blockpost_region_id).first().name))
            
            # Auto
            elif (travel_type_query.value, travel_type_query.name) in c.various_travel_types:
                self.q = self.q.join(VariousTravel)

                arrival_date = request.args.get("arrival_date", None)
                if arrival_date:
                    self.q = self.q.filter(VariousTravel.date == arrival_date)
                    self.search_form.arrival_date.default = parse_date(arrival_date)
                
                border_id = request.args.get("auto_border_id", "-1")
                if border_id != "-1":
                    self.search_form.auto_border_id.default = border_id

                border_list = [("auto_border_id", self.search_form.auto_border_id),
                               ("foot_border_id", self.search_form.foot_border_id),
                               ("sea_border_id", self.search_form.sea_border_id)]
                
                for border_type in border_list:
                    if border_type[0] in request.args:
                        if request.args[border_type[0]] != "-1":
                            border_id = request.args[border_type[0]]
                            border_type[1].default = border_id
                
                            self.q = self.q.filter(VariousTravel.border_control_id == border_id)
                            self.search_params.append((_("Граница"), BorderControl.query.filter_by(id = border_id).first().name))
                            break

        self.search_form.process()

    def print_entry(self, result):
        patient = result

        patient_id = (patient, "/patient_profile?id={}".format(patient.id))
        iin = patient.iin
        travel_type = patient.travel_type
        region = patient.region

        is_found = yes_no_html(False)
        if patient.is_found:
            is_found = yes_no_html(True)

        in_hospital = yes_no_html(False)
        if patient.in_hospital:
            in_hospital = yes_no_html(True)

        is_infected = yes_no_html(False, invert_colors=True)
        if patient.is_infected:
            is_infected = yes_no_html(True, invert_colors=True)

        created_date = patient.created_date.strftime("%d-%m-%Y %H:%M")

        contacted = ContactedPersons.query.filter_by(infected_patient_id=patient.id).all()

        contacted_found_count = 0

        for contact in contacted:
            contacted_person = Patient.query.filter_by(id=contact.contacted_patient_id).first()
            if contacted_person and contacted_person.is_found:
                contacted_found_count += 1

        contacted_count = "{}/{}".format(contacted_found_count, len(contacted))
        row_to_print = []

        if self.select_contacted:
            select_contacted_button = None

            if self.select_contacted == patient.id:
                select_contacted_button = _("Основной Пациент")
            elif patient.id in self.infected_contacted_ids:
                potential_or_close = _("Близкий Контакт") if not self.infected_contact_type[patient.id] else _("Потенциальный Контакт")

                select_contacted_html = "<a href=\"/contacted_persons?id={}\" class=\"btn btn-success\">{}</a>".format(
                                        self.select_contacted, potential_or_close)
                select_contacted_button = (select_contacted_html, "safe")                
            elif patient.id in self.contacted_infected_ids:
                potential_or_close = _("Близкий") if not self.contacted_contact_type[patient.id] else _("Потенциальный")

                select_contacted_html = "<a href=\"/contacted_persons?id={}\" class=\"btn btn-danger\">{}</a>".format(
                                        patient.id, "{} ({})".format(_("Контактировал С"), potential_or_close))
                select_contacted_button = (select_contacted_html, "safe")
            else:
                select_contacted_html = "<a href=\"/select_contacted?infected_patient_id={}&contacted_patient_id={}\" class=\"btn btn-primary\">{}</a>".format(
                                        self.select_contacted, patient.id, _("Выбрать Контактным"))
                select_contacted_button = (patient.id, "checkbox", "add_contacted_patient_id")

            if select_contacted_button:
                row_to_print.append(select_contacted_button)

        row_to_print += [patient_id, iin, travel_type, region, is_found, \
                in_hospital, is_infected, contacted_count, created_date]

        return row_to_print


    def download_xls(self):
        if not self.is_downloadable_xls:
            return None

        data = []

        for row in self.q.all():
            gender = _("Неизвестно")
            if row.gender != None:
                gender = _("Женский") if row.gender == True else _("Мужской")

            # contacted_id = [c.infected_patient_id for c in ContactedPersons.query.filter_by(contacted_patient_id=row.id).all()]
            # contacted_bool = _("Да") if len(contacted_id) else _("Нет")
            user_created = User.query.filter_by(id=row.created_by_id).first()
            user_organization = "" if not user_created else user_created.organization
            username = "" if not user_created else user_created.username

            # travel_date = ""
            travel_info = ""

            if row.travel_type:
                if row.travel_type.value == c.flight_type[0]:
                    flight_travel = FlightTravel.query.filter_by(patient_id=row.id)
                    if flight_travel.count():
                        flight_travel = flight_travel.first()
                        travel_info = flight_travel.seat
            #             travel_date = flight_travel.flight_code.date
            #             travel_info = flight_travel.flight_code.code
                elif row.travel_type.value == c.train_type[0]:
                    train_travel = TrainTravel.query.filter_by(patient_id=row.id)
                    if train_travel.count():
                        train_travel = train_travel.first()
                        travel_info = "{}-{} {}-{}".format(_("Вагон"), train_travel.wagon, _("Место"), train_travel.seat)
            #             train = train_travel.train

            #             travel_date = train.arrival_date
            #             travel_info = "{}, {} - {},{}".format(train.from_country, train.from_city,
            #                                                   train.to_country, train.to_city)
            #     elif row.travel_type.value in c.various_travel_types_values:
            #         various_travel = VariousTravel.query.filter_by(patient_id=row.id)
            #         if various_travel.count():
            #             various_travel = various_travel.first()

            #             travel_date = various_travel.date
            #             travel_info = various_travel.border_control
            #     elif row.travel_type.value == c.blockpost_type[0]:
            #         blockpost_travel = BlockpostTravel.query.filter_by(patient_id=row.id)
            #         if blockpost_travel.count():
            #             blockpost_travel = blockpost_travel.first()

            #             travel_date = blockpost_travel.date
            #             travel_info = str(blockpost_travel.region)

            is_infected = yes_no(row.is_infected)
            is_found = yes_no(row.is_found)

            data.append([row.id, str(row), row.iin, gender, row.dob, str(row.region), 
                        row.pass_num, str(row.citizenship), str(row.country_of_residence),
                        str(row.travel_type), travel_info, #travel_date,
                        str(row.home_address), row.telephone, row.email, str(row.status),
                        is_found, is_infected, row.hospital,
                        row.job, row.job_position, row.job_category, row.job_address,
                        # contacted_bool, contacted_id,
                        row.created_date.strftime("%d-%m-%Y %H:%M"), user_organization, username])

        data = pd.DataFrame(data, columns=[_("ID"), _("ФИО"), _("ИИН"), _("Пол"), _("Дата Рождения"), _("Регион"),
                                           _("Номер Паспорта"), _("Гражданство"), _("Страна Проживания"),
                                           _("Тип Въезда"), _("Инфо о Въезде"), #_("Дата Въезда"), 
                                           _("Домашний Адрес"), _("Телефон"), _("E-Mail"), _("Статус"),
                                           _("Найден"), _("Инфицирован"), _("Госпиталь"),
                                           _("Место Работы/Учебы"), _("Должность"), _("Категория Работы"),
                                           _("Адрес Работы"),
                                           #_("Контактный?"), _("Нулевой Пациент ID (Контакт)"),
                                           _("Дата Создания"), _("Организация"), _("Логин Специалиста")])

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        data.to_excel(writer, index=False)

        def get_col_widths(df):
            widths = []
            for col in df.columns:
                col_data_width = max(df[col].map(str).map(len).max(), len(col))
                col_data_width *= 1.2

                widths.append(col_data_width)
            
            return widths

        for i, width in enumerate(get_col_widths(data)):
            writer.sheets['Sheet1'].set_column(i, i, width)

        writer.save()
        xlsx_data = output.getvalue()

        region_id = int(request.args.get("region_id", -1))
        region_name = c.all_regions
        
        region_query = Region.query.filter_by(id = region_id)
        if region_query.count():
            region_name = region_query.first().name

        filename_xls = "{}_{}".format(_("пациенты"), region_name)

        date_range_start = request.args.get("date_range_start", None)
        if date_range_start:
            filename_xls = "{}_{}".format(filename_xls, date_range_start)

        date_range_end = request.args.get("date_range_end", None)
        if date_range_end:
            filename_xls = "{}_{}".format(filename_xls, date_range_end)

        filename_xls = "{}.xls".format(filename_xls)
        
        response = Response(xlsx_data, mimetype="application/vnd.ms-excel")
        response.headers["Content-Disposition"] = \
            "attachment;" \
            "filename*=UTF-8''{}".format(urllib.parse.quote(filename_xls.encode('utf-8')))

        return response