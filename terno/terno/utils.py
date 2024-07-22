import terno.models as models
from django.views.decorators.cache import cache_page
from sqlshield.shield import Session
from sqlshield.models import MDatabase
import sqlalchemy
from terno.llm.base import LLMFactory


def prepare_mdb(datasource, roles):
    allowed_tables, allowed_columns = get_admin_config_object(datasource, roles)

    mDb = generate_mdb(datasource)
    mDb.keep_only_tables(allowed_tables.values_list('pub_name', flat=True))
    # mDb.keep_only_columns(allowed_columns)

    tables = mDb.get_table_dict()
    update_filters(tables, datasource, roles)

    return mDb


def _get_base_filters(datasource):
    tbl_base_filters = {}
    for trf in models.TableRowFilter.objects.filter(data_source=datasource):
        filter_str = trf.filter_str.strip()
        if len(filter_str) > 0:
            tbl_base_filters[trf.table.name] = ["(" + filter_str + ")"]
    return tbl_base_filters


def _get_grp_filters(datasource, roles):
    tbls_grp_filter = {}  # key: table_name, value = [filter1, filter2]
    for gtrf in models.GroupTableRowFilter.objects.filter(data_source=datasource, group__in=roles):
        filter_str = gtrf.filter_str.strip()
        if len(filter_str) > 0:
            tbl_name = gtrf.table.name
            lst = []
            if tbl_name not in tbls_grp_filter:
                tbls_grp_filter[tbl_name] = lst
            else:
                lst = tbls_grp_filter[tbl_name]
            lst.append("(" + filter_str + ")")
    return tbls_grp_filter


def _merge_grp_filters(tbl_base_filters, tbls_grp_filter):
    '''
    Updates the row filter for each table in tables based on TableRowFIlter or GroupTableFilter.
    argument `tables' should be a dictionary of name and Mtable.

    '''
    for tbl, grp_filters in tbls_grp_filter.items():
        role_filter_str = " ( " + ' OR '.join(grp_filters) + " ) "
        all_filters = []
        if tbl in tbl_base_filters:
            all_filters = tbl_base_filters[tbl]
        else:
            tbl_base_filters[tbl] = all_filters
        all_filters.append(role_filter_str)


def update_filters(tables, datasource, roles):
    tbl_base_filters = _get_base_filters(datasource) # table_name -> ["(a=2)", "(x = 1) or (y = 2)"]
    tbls_grp_filter = _get_grp_filters(datasource, roles)
    _merge_grp_filters(tbl_base_filters, tbls_grp_filter)
    for tbl, filters_list in tbl_base_filters.items():
        if len(filters_list) > 0:
            tables[tbl].filters = 'WHERE ' + ' AND '.join(filters_list)


def get_all_group_tables(datasource, roles):
    table_object = models.PrivateTableSelector.objects.filter(
        data_source=datasource).first()
    global_tables = models.Table.objects.filter(
        data_source=datasource)
    if table_object:
        global_tables_ids = table_object.tables.all().values_list('id', flat=True)
        global_tables = global_tables.exclude(id__in=global_tables_ids)

    group_tables_object = models.GroupTableSelector.objects.filter(
        group__in=roles,
        tables__data_source=datasource).first()
    if group_tables_object:
        group_tables = group_tables_object.tables.all()
        all_group_tables = global_tables.union(group_tables)
    else:
        all_group_tables = global_tables
    return all_group_tables


# @cache_page(24*3600)
def get_admin_config_object(datasource, roles):
    """
    Return Tables and columns accessible for user
    """
    all_group_tables = get_all_group_tables(datasource, roles)
    all_group_tables_ids = list(all_group_tables.values_list('id', flat=True))
    table_columns = models.TableColumn.objects.filter(table_id__in=all_group_tables_ids)
    group_columns_object = models.GroupColumnSelector.objects.filter(
        group__in=roles,
        columns__in=table_columns).first()
    if group_columns_object:
        group_columns = group_columns_object.columns.all()
    else:
        group_columns = table_columns
    return all_group_tables, group_columns


def llm_response(question, schema_generated):
    try:
        llm = LLMFactory.create_llm()
        generated_sql = llm.get_response(question, schema_generated)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    return {'status': 'success', 'generated_sql': generated_sql}


# @cache_page(24*3600)
def generate_mdb(datasource):
    engine = sqlalchemy.create_engine(datasource.connection_str)
    inspector = sqlalchemy.inspect(engine)
    mDb = MDatabase.from_inspector(inspector)
    return mDb


def generate_native_sql(mDb, aSql):
    d = {'company': '\'Telus\''}
    sess = Session(mDb, d)
    try:
        gSQL = sess.generateNativeSQL(aSql)
        #print("Native SQL: ", gSQL)
        status = 'success'
        return status, gSQL
    except Exception as e:
        status = 'failed'
        error = e.args[0]
        return status, error


def execute_native_sql(datasource, gSQL):
    engine = sqlalchemy.create_engine(datasource.connection_str)
    with engine.connect() as con:
        try:
            rs = con.execute(sqlalchemy.text(gSQL))
            status = 'success'
        except Exception as e:
            status = 'failed'
            error = e.args[0]
            return status, error
        table_data = {}
        table_data['columns'] = list(rs.keys())
        table_data['data'] = []
        for row in rs:
            data = {}
            for i, column in enumerate(table_data['columns']):
                data[column] = row[i]
            table_data['data'].append(data)
        return status, table_data
