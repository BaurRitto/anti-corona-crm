# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db
from app.main.models import Region
from app.main.users.forms import CreateUserForm, UpdateUserForm
from app.main.forms import TableSearchForm
import math
from app.login.models import User
from app.main.util import get_regions, get_regions_choices
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c
from sqlalchemy import exc

@blueprint.route('/users', methods=['GET'])
@login_required
def users():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500

    form = TableSearchForm()
    regions = get_regions(current_user)

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    users = []
    filt = dict()

    q = User.query

    page = 1
    per_page = 5
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()

    users = q.offset((page-1)*per_page).limit(per_page).all()

    max_page = math.ceil(total_len/per_page)

    change = None
    error_msg = None

    if "added_user" in request.args:
        change =_("Пользователь был успешно добавлен")
    elif "delete_user" in request.args:
        change =_("Пользователь был успешно удален")

    form.process()
    return route_template('users/users', users=users, form=form, page=page, max_page=max_page, 
                                        total = total_len, constants=c, change=change, error_msg=error_msg)

@blueprint.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        

    patient_form = CreateUserForm()
    regions = get_regions(current_user)

    if not patient_form.region_id.choices:
        patient_form.region_id.choices = [(r.id, r.name) for r in regions]

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=False)
        
        user = User.query.filter_by(username=new_dict['username'][0]).first()
        if user:
            return route_template( 'users/add_user', error_msg=_('Имя пользователя уже зарегистрировано'), form=patient_form, change=None)

        user = User(**new_dict)
        
        db.session.add(user)
        db.session.commit()

        return redirect("{}?added_user".format(url_for('main_blueprint.users')))
    else:
        return route_template( 'users/add_user', form=patient_form, change=None, error_msg=None)


@blueprint.route('/user_profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        

    if "id" in request.args:
        user_query = User.query.filter_by(id=request.args["id"])
        user = user_query.first()
        
        if not user:
            return render_template('errors/error-404.html'), 404
        else:
            form = UpdateUserForm()
            
            change = None
            error_msg = None
            
            if 'update' in request.form:
                values = request.form.to_dict()

                if values['username']:
                    new_username = values['username']
                    
                    if not new_username == user.username:  
                        if not User.query.filter_by(username = new_username).count():
                            user.username = new_username
                        else:
                            error_msg = _("Пользователь с таким логином уже существует")

                if not error_msg:
                    if values['password']:
                        password = values['password']

                        user.password = hash_pass(password)

                    del values["password"]
                    del values["csrf_token"]
                    del values["update"]
                    
                    user_query.update(values)

                    db.session.add(user)
                    db.session.commit()

                    change = _("Данные обновлены")

            form.full_name.default = user.full_name
            form.username.default = user.username

            form.email.default = user.email
            form.telephone.default = user.telephone
            
            form.region_id.choices = get_regions_choices(current_user)
            form.region_id.default = user.region_id
            form.organization.default = user.organization
  
            form.process()
            return route_template('users/user_profile', form = form, user=user, change=change, error_msg=error_msg)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        
    
    if len(request.form):
        if "delete" in request.form:
            user_id = request.form["delete"]
            user = None
            try:
                user = User.query.filter(User.id == user_id)
            except exc.SQLAlchemyError:
                pass

            if user:
                user.delete()
                db.session.commit()

    return redirect("{}?delete_user".format(url_for('main_blueprint.users')))