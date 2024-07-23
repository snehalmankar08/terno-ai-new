from django.shortcuts import render, redirect
from django.http import JsonResponse
import terno.models as models
import terno.utils as utils
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.exceptions import ObjectDoesNotExist


@login_required
def index(request):
    return render(request, 'frontend/index.html')


@ensure_csrf_cookie
def login_page(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('terno:index')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'frontend/index.html')


def settings(request):
    return render(request, 'frontend/index.html')


@login_required
def get_datasources(request):
    datasources = models.DataSource.objects.filter(enabled=True)
    data = [{'name': d.display_name, 'id': d.id} for d in datasources]
    return JsonResponse({
        'datasources': data
    })


@login_required
def get_sql(request):
    data = json.loads(request.body)
    datasource_id = data.get('datasourceId')
    question = data.get('prompt')

    try:
        datasource = models.DataSource.objects.get(id=datasource_id,
                                                   enabled=True)
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'error': 'No Datasource found.'
        })
    roles = request.user.groups.all()

    mDB = utils.prepare_mdb(datasource, roles)
    schema_generated = mDB.generate_schema()
    llm_response = utils.llm_response(question, schema_generated)

    if llm_response['status'] == 'error':
        return JsonResponse({
            'status': llm_response['status'],
            'error': llm_response['error'],
        })

    return JsonResponse({
        'status': llm_response['status'],
        'generated_sql': llm_response['generated_sql'],
    })


@login_required
def execute_sql(request):
    data = json.loads(request.body)
    user_sql = data.get('sql')
    datasource_id = data.get('datasourceId')

    try:
        datasource = models.DataSource.objects.get(id=datasource_id,
                                                   enabled=True)
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'error': 'No Datasource found.'
        })
    roles = request.user.groups.all()

    mDB = utils.prepare_mdb(datasource, roles)

    native_sql_response = utils.generate_native_sql(mDB, user_sql)

    if native_sql_response['status'] == 'error':
        return JsonResponse({
            'status': native_sql_response['status'],
            'error': native_sql_response['error'],
        })

    execute_sql_response = utils.execute_native_sql(
        datasource, native_sql_response['native_sql'])

    if execute_sql_response['status'] == 'error':
        return JsonResponse({
            'status': execute_sql_response['status'],
            'error': execute_sql_response['error'],
        })

    return JsonResponse({
        'status': execute_sql_response['status'],
        'table_data': execute_sql_response['table_data']
    })


@login_required
def get_tables(request, datasource_id):
    if datasource_id:
        datasource = models.DataSource.objects.get(id=datasource_id)
    else:
        datasource = models.DataSource.objects.first()
    role = request.user.groups.all()
    allowed_tables, allowed_columns = utils.get_admin_config_object(datasource, role)
    table_data = []
    for table in allowed_tables:
        column = allowed_columns.filter(table_id=table)
        column_data = list(column.values('name', 'data_type'))
        result = {
            'table_name': table.name,
            'column_data': column_data
        }
        table_data.append(result)
    return JsonResponse({
        'table_data': table_data
    })


@login_required
def get_user_details(request):
    user = request.user
    return JsonResponse({
        'id': user.id,
        'username': user.username
    })
