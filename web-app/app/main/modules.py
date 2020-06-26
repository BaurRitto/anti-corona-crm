from flask import request
import math
from wtforms import SelectField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm

class TableModule:
    class WrongPageError(Exception):
        pass

    class WrongSortingParameterError(Exception):
        pass

    class TableForm(FlaskForm):
        per_page = SelectField(choices=[(num, str(num)) for num in [5, 10, 25, 50, 100, 250, 500]], 
                                default=5, validators=[DataRequired()])

    def __init__(self, request, q, table_head, header_button = None, search_form = None, sort_param = None,
                page = 1, per_page = 5, table_title = "", is_downloadable_xls = False, table_head_info = dict()):
        if "page" in request.args:
            try:
                page = int(request.args["page"])
            except ValueError:
                raise self.WrongPageError

        self.page = page
        self.per_page = per_page
        self.table_head_dict = table_head
        self.table_head = []
        self.request = request
        self.q = q
        self.header_button = header_button
        self.search_form = search_form
        self.sort_param = sort_param

        self.search_params = []
        
        self.is_downloadable_xls = is_downloadable_xls
        self.xls_response = None

        self.table_head_info = table_head_info

        self.table_title = table_title

        self.table_form = self.TableForm()
        try:
            per_page = request.args.get("per_page", None)
            if per_page:
                per_page = int(per_page)
                self.table_form.per_page.default = per_page
                self.per_page = per_page
        except ValueError:
            print("Wrong Per Page Value")        

        if page < 1:
            raise self.WrongPageError
        self.table_form.process()

        self.total_len = q.count()
        self.max_page = 0

        self.search_table()
        self.sort_table()

        download_xls = request.args.get("download_xls", None)
        if download_xls == self.__class__.__name__:
            self.xls_response = self.download_xls()

        # Should always be the last one to be called
        self.entries = self.get_entries()

    def print_entry(self, result):
        pass

    def get_entries(self):
        if self.total_len:
            entries = []

            self.total_len = self.q.count()
            
            for result in self.q.offset((self.page-1)*self.per_page).limit(self.per_page).all():
                entry = {"data": self.print_entry(result)}
                entries.append(entry)

            entries = self.preprocess_entries(entries)

            self.max_page = math.ceil(self.total_len/self.per_page)

            return entries

    def preprocess_entries(self, entries):
        return entries

    def search_table(self):
        pass

    def download_xls(self):
        pass

    def sort_table(self):
        self.sort_by = None
        self.sort_by_asc = True
        
        if "sort_by_asc" in request.args:
            self.sort_by = request.args["sort_by_asc"]
        elif "sort_by_desc" in request.args:
            self.sort_by = request.args["sort_by_desc"]
            self.sort_by_asc = False

        for i, th in enumerate(self.table_head_dict):
            new_th = (th, th) if len(self.table_head_dict[th]) > 0 else th
            self.table_head.append(new_th)

        first = self.q.first()

        if first and self.sort_param != None:
            first = getattr(first, self.sort_param)

        if len(self.q._entities) == 1:
            first = [first]
        if self.sort_by:
            if first:
                for m in first:
                    if self.sort_by in self.table_head_dict:
                        for s in self.table_head_dict[self.sort_by]:
                            if hasattr(m, "__dict__"):
                                if s in m.__dict__.keys():
                                    param = getattr(type(m), s)
                                    if self.sort_by_asc:
                                        self.q = self.q.order_by(param.asc())
                                    else:
                                        self.q = self.q.order_by(param.desc())