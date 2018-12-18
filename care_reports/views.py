from django.http import (
    HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, render, get_object_or_404
from django.template import RequestContext, loader
# from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
import json
import sys
from collections import OrderedDict

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.db import connection
import HTML
import datetime
import decimal
from onadata.apps.usermodule.views_project import get_viewable_projects
from onadata.apps.usermodule.views import get_organization_by_user
from onadata.apps.usermodule.models import UserModuleProfile, Organizations
from onadata.apps.approval.models.approval import InstanceApproval

import xlwt

from django.http import HttpResponse
from django.contrib.auth.models import User


def get_report_operation_status(request):
    list_of_list = []
    startDate = ''
    endDate = ''
    submitter = '%'
    filter_org_id = '%'

    if request.method == 'POST':
        startDate = request.POST.get("start_date", "")
        endDate = request.POST.get("end_date", "")
        submitter = request.POST.get("submitter", "")
        filter_org_id = request.POST.get("org_id", "%")

    xforms = get_viewable_projects(request)
    # print xforms
    # print submitted_by
    c = connection.cursor()
    try:
        c.execute("BEGIN")
        c.callproc("approval_status_new", (str(startDate), str(endDate), str(submitter), str(filter_org_id)))
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()
    # print results
    for each in results:
        for xform in xforms:
            if str(each[0]) == xform.id_string:
                tmp_list = [xform.title, each[1], each[2], each[3], each[4]]
                list_of_list.append(tmp_list)

                # print list_of_list
    header_row = ['Form', 'Submitted', 'Pending', 'Approved', 'Rejected']
    htmlcode = get_all_submitted_values_as_table(list_of_list, header_row)
    # print htmlcode
    submitted_by = InstanceApproval.objects.values_list('senderid', flat=True).distinct()
    org_id_list = get_organization_by_user(request.user)
    org_filter_list = {}
    for org_id in org_id_list:
        organization = get_object_or_404(Organizations, id=org_id)
        org_filter_list[org_id] = str(organization.organization)
    print('org_list', org_id_list)
    print('org_list', org_filter_list)
    variables = RequestContext(request, {
        'status_table': htmlcode,
        'submitted_by': submitted_by,
        'org_filter_list': org_filter_list,
    })
    if request.is_ajax():
        return HttpResponse(htmlcode)

    output = render(request, 'approval_status_summary.html', variables);
    return HttpResponse(output)


def get_all_submitted_values_as_table(data_list, table_headers):
    htmlcode = HTML.table(data_list, header_row=table_headers, col_width=['50%', '10%' '10%', '10%', '10%'],
                          col_align=['left', 'center', 'center', 'center', 'center']
                          )
    return_html = str(htmlcode).replace('<TABLE', '<TABLE class="sortable" id="sortable"')
    return return_html


def get_report_np_attendence_activity(request):
    pngo_name = '%'
    village_name = '%'
    ff_name = '%'
    boundary = '%'
    is_export = False
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        village_name = request.POST.get('vdc')
        ff_name = request.POST.get('ff_name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        boundary = request.POST.get('boundary')
        is_export = request.POST.get('is_export')

    if (ff_name is None or len(ff_name) == 0):
        ff_name = '%'

    c = connection.cursor()
    try:
        c.execute("BEGIN")
        c.callproc("get_care_np_new_attend_activity_activities",
                   [pngo_name, village_name, ff_name, start_date, end_date, str(boundary)])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    if request.is_ajax():
        if is_export is not None and bool(is_export) is True:
            wb = get_excel_file(results)
            http_response = HttpResponse(content_type='application/ms-excel')
            http_response['Content-Disposition'] = 'attachment; filename="attendance.xls"'
            wb.save(http_response)
            return http_response
        jsonData = {}
        jsonData[str('data_list')] = results
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    filter_json = get_report_filters_value(request, 'np')

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'data_list': json.dumps(results),
        'filter_json': filter_json,
        'rpt_type': 'np'
    })

    output = render(request, 'attendence_activity_report_np.html', variables);
    return HttpResponse(output)


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def get_report_bd_outcome_others_journal(request):
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    c = connection.cursor()

    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_new_outcomejournal_otheract", [start_date, end_date])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    filter_json = get_report_filters_value(request, 'bd')

    if request.is_ajax():
        jsonData = {}
        jsonData[str('data_list')] = results
        return HttpResponse(json.dumps(jsonData, default=decimal_default), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'data_list': json.dumps(results, default=decimal_default),
        'filter_json': filter_json,
        'rpt_type': 'bd'
    })
    output = render(request, 'attendence_outcome_others.html', variables);
    return HttpResponse(output)


def get_report_bd_outcome_adolescent_journal(request):
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    bp = '%'

    if request.is_ajax():
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        bp = request.POST.get('bp')

    c = connection.cursor()

    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_new_outcomejournal_topics", [start_date, end_date, bp])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    print(json.dumps(results, default=decimal_default))
    filter_json = get_report_filters_value(request, 'bd')

    if request.is_ajax():
        jsonData = {}
        jsonData[str('data_list')] = results
        return HttpResponse(json.dumps(jsonData, default=decimal_default), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'data_list': json.dumps(results, default=decimal_default),
        'filter_json': filter_json,
        'rpt_type': 'bd'
    })
    output = render(request, 'attendence_adolescent.html', variables);
    return HttpResponse(output)


def get_report_np_outcome_adolescent_journal(request):
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    c = connection.cursor()

    try:
        qry = "with p as(with t as(select json_array_elements((json->>'mainAct')::json) mainact from logger_instance where xform_id=307) select mainact->>'mainAct/tb1_month' act_month,string_agg(distinct (mainact->>'mainAct/tb1_Activities'),', ') act_act_plan,string_agg(distinct (mainact->>'mainAct/tb1_target'),', ') act_target,string_agg(distinct (mainact->>'mainAct/tb1_actAcieve'),', ') act_ach from t where (mainact->>'mainAct/tb1_month')::Date between '" + str(
            start_date) + "' and '" + str(
            end_date) + "' group by mainact->>'mainAct/tb1_month' order by 1,2) select '' as _pngo, act_month,act_act_plan,act_target,act_ach from p;"

        c.execute(qry)
        results = c.fetchall()

    finally:
        c.close()

    filter_json = get_report_filters_value(request, 'np')

    if request.is_ajax():
        jsonData = {}
        jsonData[str('data_list')] = results
        return HttpResponse(json.dumps(jsonData, default=decimal_default), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'data_list': json.dumps(results, default=decimal_default),
        'filter_json': filter_json,
        'rpt_type': 'np'
    })
    output = render(request, 'np_attendence_adolescent.html', variables);
    return HttpResponse(output)


def get_report_bd_outcome_journal(request):
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    data_list = []
    c = connection.cursor()

    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_new_outcomejournal_attendance", [start_date, end_date])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

        for each in results:
            data = []
            data.append(each[0])
            data.append(each[1])
            data.append(each[2])
            data.append(each[3])
            data_list.append(data)
    print(json.dumps(data_list))
    filter_json = get_report_filters_value(request, 'bd')

    col_width = ['30%', '25%', '25%']

    if request.is_ajax():
        jsonData = {}
        jsonData[str('data_list')] = data_list
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'data_list': json.dumps(data_list),
        'filter_json': filter_json,
        'rpt_type': 'bd'
    })
    output = render(request, 'attendence_outcome_girl_report.html', variables);
    return HttpResponse(output)


def get_report_bd_adolescents_status(request):
    pngo_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    table_headers_others = ['Type of changes', 'No of adolescent girls',
                            'No of adolescent boys']

    c = connection.cursor()

    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_adolescents_status",
                   [pngo_name, upzilla_name, union_name, village_name, start_date, end_date])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    filter_json = get_report_filters_value(request, 'bd')
    col_width = ['45%', '35%', '35%', '1%']
    adolescent_table = get_html_table(results, table_headers_others, col_width)
    if request.is_ajax():
        jsonData = {}
        jsonData[str('adolescent_table')] = adolescent_table
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'adolescent_table': adolescent_table,
        'filter_json': filter_json,
        'rpt_type': 'bd'
    })

    output = render(request, 'attendence_adolescents_report.html', variables);
    return HttpResponse(output)

import pandas

def get_report_np_adolescents_status(request):
    pngo_name = '%'
    village_name = '%'
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        print("SDADD")
        pngo_name = request.POST.get('pngo')
        village_name = request.POST.get('vdc')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    table_headers_others = ['Type of changes', 'No of adolescent girls',
                            'No of adolescent boys']

    c = connection.cursor()

    try:
        c.execute("BEGIN")
        c.callproc("get_care_np_adolescents_status",
                   [pngo_name, village_name, start_date, end_date])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    filter_json = get_report_filters_value(request, 'np')
    col_width = ['45%', '40%', '40%','1%']
    adolescent_table = get_html_table(results, table_headers_others, col_width)

    ###############
    main_query = "WITH p AS( SELECT json->>'detail/statusChange' changestatus, json->>'detail/sex' gender FROM PUBLIC.logger_instance WHERE xform_id = 321 and deleted_at is null AND (json->>'_submission_time')::timestamp::date BETWEEN '" + str(
        start_date) + "' AND '" + str(end_date) + "' AND json->>'profile/pngo' LIKE '" + str(
        pngo_name) + "' AND json->>'profile/vdc' LIKE '" + str(
        village_name) + "')SELECT num changestatus, Count( CASE gender WHEN '1' THEN gender END) AS girls, Count( CASE gender WHEN '2' THEN gender END) AS boys FROM (VALUES (1), (2), (3),(4),(5),(6),(7)) as k(num) left join p on k.num::text = p.changestatus GROUP BY num order by num"
    df = pandas.DataFrame()
    df = pandas.read_sql(main_query, connection)
    girls = df.girls.tolist()
    boys = df.boys.tolist()

    if request.is_ajax():
        jsonData = {}
        jsonData[str('adolescent_table')] = adolescent_table
        jsonData['girls'] = girls
        jsonData['boys'] = boys
        return HttpResponse(json.dumps(jsonData), content_type='application/json')

    variables = RequestContext(request, {
        'girls':girls,
        'boys':boys,
        'head_title': 'Project Summary',
        'adolescent_table': adolescent_table,
        'filter_json': filter_json,
        'rpt_type': 'np'
    })

    output = render(request, 'attendence_adolescents_report.html', variables);
    return HttpResponse(output)


def get_report_bd_others_activities(request):
    pngo_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    is_export = False
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_export = request.POST.get('is_export')

    table_headers_others = ['Other activities', 'No/frequency of activity',
                            'Attendance Male', 'Attendance Female', 'Total Attendance', 'Average Attendance']
    data_list = []
    c = connection.cursor()

    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_new_attend_activity_others",
                   [pngo_name, upzilla_name, union_name, village_name, start_date, end_date])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    for each in results:
        data = []
        if each[0] is None:
            data.append("")
        else:
            data.append(each[0].encode('utf-8'))
        data.append(each[1])
        data.append(each[2])
        data.append(each[3])
        data.append(each[4])
        if each[1] == 0:
            data.append(each[4])
        else:
            data.append((each[4] / each[1]))
        data_list.append(data)
    filter_json = get_report_filters_value(request, 'bd')
    print(json.dumps(data_list))
    col_width = ['20%', '15%', '15%', '15%', '15%']
    others_table = get_html_table(data_list, table_headers_others, col_width)
    if request.is_ajax():
        jsonData = {}
        jsonData[str('others_table')] = others_table
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'others_table': others_table,
        'filter_json': filter_json,
        'rpt_type': 'bd'
    })

    output = render(request, 'attendence_other_report.html', variables);
    return HttpResponse(output)


def get_report_np_others_activities(request):
    pngo_name = '%'
    village_name = '%'
    is_export = False
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        village_name = request.POST.get('vdc')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_export = request.POST.get('is_export')

    table_headers_others = ['Other activities', 'No/frequency of activity',
                            'Attendance Male', 'Attendance Female', 'Total Attendance', 'Average Attendance']
    data_list = []
    c = connection.cursor()

    try:

        c.execute("BEGIN")
        c.callproc("get_care_np_new_attend_activity_others", [pngo_name, village_name, start_date, end_date])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    for each in results:
        data = []
        if each[0] is None:
            data.append("")
        else:
            data.append(each[0].encode('utf-8'))
        data.append(each[1])
        data.append(each[2])
        data.append(each[3])
        data.append(each[4])
        if each[1] is not None and each[4] is not None:
            if each[1] == 0:
                data.append(each[4])
            else:
                data.append((each[4] / each[1]))
        data_list.append(data)
    print(results)
    filter_json = get_report_filters_value(request, 'np')
    print(json.dumps(data_list))
    col_width = ['20%', '15%', '15%', '15%', '15%']
    others_table = get_html_table(data_list, table_headers_others, col_width)
    if request.is_ajax():
        jsonData = {}
        jsonData[str('others_table')] = others_table
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'others_table': others_table,
        'filter_json': filter_json,
        'rpt_type': 'np'
    })

    output = render(request, 'attendence_other_report.html', variables)
    return HttpResponse(output)


def get_report_np_attendence_topic(request):
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    bp = '%'

    if request.is_ajax():
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        bp = request.POST.get('bp')

    table_headers_topic = ['Name of Main Topic/session covered', 'Frequency (number of sessions) DSDC',
                           'Frequency (number of sessions) SSS']

    c = connection.cursor()
    try:
        c.execute("BEGIN")
        c.callproc("get_care_np_attend_activity_topics", [start_date, end_date, bp])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()
    print('result')
    print(results)
    col_width = ['30%', '25%', '25%']
    topic_table = get_html_table(results, table_headers_topic, col_width)
    if request.is_ajax():
        jsonData = {}
        jsonData[str('topic_table')] = topic_table
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'topic_table': topic_table,
        'rpt_type': 'np'
    })

    output = render(request, 'attendence_topic_report_np.html', variables);
    return HttpResponse(output)


def get_report_bd_attendence_topic(request):
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        bp = request.POST.get('bp')

    table_headers_topic = ['Name of Main Topic/session covered', 'Frequency (number of sessions) ASD',
                           'Frequency (number of sessions) JASHIS']

    c = connection.cursor()
    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_attend_activity_topics", [start_date, end_date, bp])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()
    print('result')
    print(results)
    col_width = ['30%', '25%', '25%']
    topic_table = get_html_table(results, table_headers_topic, col_width)
    if request.is_ajax():
        jsonData = {}
        jsonData[str('topic_table')] = topic_table
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'topic_table': topic_table,
        'rpt_type': 'bd'
    })

    output = render(request, 'attendence_topic_report.html', variables);
    return HttpResponse(output)


def get_report_bd_attendence_topic(request):
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    bp = '%'

    if request.is_ajax():
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        bp = request.POST.get('bp')

    table_headers_topic = ['Name of Main Topic/session covered', 'Frequency (number of sessions) ASD',
                           'Frequency (number of sessions) JASHIS']

    c = connection.cursor()
    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_attend_activity_topics", [start_date, end_date, bp])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()
    # print ('result')
    # print (results)
    col_width = ['30%', '25%', '25%']
    topic_table = get_html_table(results, table_headers_topic, col_width)
    if request.is_ajax():
        jsonData = {}
        jsonData[str('topic_table')] = topic_table
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'topic_table': topic_table,
        'rpt_type': 'bd'
    })

    output = render(request, 'attendence_topic_report.html', variables);
    return HttpResponse(output)


'''
    This method is used to view table data for average attendance from main session and sub-activity
    where filtered categories are PNGO, Boundary Partner, Upazila, Union, Village, FF, Date Range
'''


def get_report_bd_attendence_activity(request):
    pngo_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    ff_name = '%'
    boundary = '%'
    is_export = False
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        ff_name = request.POST.get('ff_name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        boundary = request.POST.get('boundary')
        is_export = request.POST.get('is_export')

    if (ff_name is None or len(ff_name) == 0):
        ff_name = '%'

    print[pngo_name, upzilla_name, union_name, village_name, ff_name, start_date, end_date, str(boundary)]
    c = connection.cursor()
    try:
        c.execute("BEGIN")
        c.callproc("get_care_bd_new_attend_activity_activities",
                   [pngo_name, upzilla_name, union_name, village_name, ff_name, start_date, end_date, str(boundary)])
        results = c.fetchall()
        c.execute("COMMIT")
    finally:
        c.close()

    if request.is_ajax():
        if is_export is not None and bool(is_export) is True:
            wb = get_excel_file(results)
            http_response = HttpResponse(content_type='application/ms-excel')
            http_response['Content-Disposition'] = 'attachment; filename="attendance.xls"'
            wb.save(http_response)
            return http_response
        jsonData = {}
        jsonData[str('data_list')] = results
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    filter_json = get_report_filters_value(request, 'bd')

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'data_list': json.dumps(results),
        'filter_json': filter_json,
        'rpt_type': 'bd'
    })

    output = render(request, 'attendence_activity_report.html', variables);
    return HttpResponse(output)


def get_report_bd_attendence_activity_old(request):
    table_headers_girls = ['Girls Group', '10-12', '13-15', '16-17', 'Total Avg', 'Hindu', 'Muslim']
    table_headers_boys = ['Boys Group', '10-12', '13-15', '16-17', 'Total Avg', 'Hindu', 'Muslim']
    table_headers_activities = ['Activities', 'Male', 'Female', 'Total', 'Male Avg', 'Female Avg', 'Total Avg']
    data_list_activities = [
        ['Activity with Role Model', '0', '0', '0', '0', '0', '0'],
        ['Advocacy-District Level on allocation on services for Adolescent', '0', '0', '0', '0', '0', '0'],
        # ['Arrange Fair','0','0','0','0','0','0'],
        # ['Awareness building by campaign','0','0','0','0','0','0'],
        ['Campaign on "Amrao Korchi', '0', '0', '0', '0', '0', '0'],
        ['Campaign with fathers on fatherhood in collaboration', '0', '0', '0', '0', '0', '0'],
        ['Campaign-Activities-Drama', '0', '0', '0', '0', '0', '0'],
        ['Campaign-Activities-Flim Show', '0', '0', '0', '0', '0', '0'],
        ['Campaign-Activities-USE of IEC materials', '0', '0', '0', '0', '0', '0'],
        ['Community dialogue /Talk Show', '0', '0', '0', '0', '0', '0'],
        ['Conduct quarterly sharing meeting', '0', '0', '0', '0', '0', '0'],
        ['Coordination meeting (UP,UNO office)', '0', '0', '0', '0', '0', '0'],
        ['Create space for potential adolescent girls to use journalist training', '0', '0', '0', '0', '0', '0'],
        ['Cross learning visit  among  EVAW Forum members', '0', '0', '0', '0', '0', '0'],
        ['Cross learning visit within Fun Centre (boys)', '0', '0', '0', '0', '0', '0'],
        ['Cross learning visit within Fun Centre (girls)', '0', '0', '0', '0', '0', '0'],
        ['Day observance', '0', '0', '0', '0', '0', '0'],
        ['Demonstrate drama', '0', '0', '0', '0', '0', '0'],
        ['Ensure birth registration (Age10-17)', '0', '0', '0', '0', '0', '0'],
        ['Exit Workshop/meeting at villages & Upazila', '0', '0', '0', '0', '0', '0'],
        ['Forum Theatre Show', '0', '0', '0', '0', '0', '0'],
        ['Fun Center group leader orientation -boys', '0', '0', '0', '0', '0', '0'],
        ['Fun Center group leader orientation-girls', '0', '0', '0', '0', '0', '0'],
        ['GED training with CV,CF', '0', '0', '0', '0', '0', '0'],
        ['Learning and reflection with adolescents and EVAW Forum members', '0', '0', '0', '0', '0', '0'],
        ['Meeting with EVAW Forum and other GO, NGO', '0', '0', '0', '0', '0', '0'],
        ['Organize masculinity and sexuality training  (FF,SCM & CV,CF)', '0', '0', '0', '0', '0', '0'],
        ['Reflection workshop between EVAW and other local  elite and religious leader.', '0', '0', '0', '0', '0', '0'],
        ['Resposive parenting (TBD)', '0', '0', '0', '0', '0', '0'],
        ['Session with EVAW Forum', '0', '0', '0', '0', '0', '0'],
        ['Session with Fathers Group', '0', '0', '0', '0', '0', '0'],
        ['Session with Mothers Group', '0', '0', '0', '0', '0', '0'],
        ['Sharing with local NGOs', '0', '0', '0', '0', '0', '0'],
        ['Spot Meeting', '0', '0', '0', '0', '0', '0'],
        ['Tea Stall meeting', '0', '0', '0', '0', '0', '0'],
        ['Workshop for sharing positive practices of marriage registers', '0', '0', '0', '0', '0', '0'],
        ['Other', '0', '0', '0', '0', '0', '0']]

    pngo_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    ff_name = '%'
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        ff_name = request.POST.get('ff_name', '%')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        # print 'Ajax calling serve it...'
    question_name = []
    funcenter_boundary_list = []
    funcenter_week = []
    funcenter_attenAge16_17 = []
    funcenter_attenAge13_15 = []
    funcenter_attenAge10_12 = []
    funcenter_attenMuslim = []
    funcenter_attenHindu = []
    otherAct_activities = []
    otherAct_attenMale = []
    otherAct_attenFemale = []
    otherAct_attenTotal = []

    raw_query = "select instance_parse_data.question,instance_parse_data.qvalue_json->>'question_value' as value from instance_parse_data,logger_instance where instance_parse_data.instance_id=logger_instance.id"
    sub_query = " and logger_instance.json->>'geo/pngo'::text like '" + pngo_name + "' and logger_instance.json->>'geo/upazila'::text like '" + upzilla_name + "' and logger_instance.json->>'geo/union'::text like '" + union_name + "' and logger_instance.json->>'geo/village'::text like '" + village_name + "' and logger_instance.json->>'geo/ffName'::text like '%" + ff_name + "%' and (logger_instance.json->>'_submission_time')::timestamp::date between '" + start_date + "' and '" + end_date + "' and (instance_parse_data.question like 'funcenter_boundaryPart' or instance_parse_data.question like 'funcenter_attenAge16_17' or instance_parse_data.question like 'funcenter_attenMuslim' or instance_parse_data.question like 'funcenter_attenAge13_15' or instance_parse_data.question like 'funcenter_attenAge10_12' or instance_parse_data.question like 'funcenter_week' or instance_parse_data.question like 'funcenter_attenHindu' or instance_parse_data.question like 'otherAct_attenFemale' or instance_parse_data.question like 'otherAct_attenMale' or instance_parse_data.question like 'otherAct_attenTotal' or instance_parse_data.question like 'otherAct_activities') "
    full_query = raw_query + sub_query
    print
    full_query
    cursor = connection.cursor()
    cursor.execute(full_query)
    db_ret_value = cursor.fetchall()
    # print db_ret_value
    for every in db_ret_value:
        q_val = every[0]
        # print q_val
        split_val = every[1].split(',')
        question_name.append(q_val)
        if q_val == 'funcenter_boundaryPart':
            for val in split_val:
                funcenter_boundary_list.append(val)
        if q_val == 'funcenter_week':
            for val in split_val:
                funcenter_week.append(val)
                # funcenter_week = [val for val in split_val]
        if q_val == 'funcenter_attenAge16_17':
            for val in split_val:
                funcenter_attenAge16_17.append(val)
                # funcenter_attenAge16_17 = [val for val in split_val]
        if q_val == 'funcenter_attenAge13_15':
            for val in split_val:
                funcenter_attenAge13_15.append(val)
                # funcenter_attenAge13_15 = [val for val in split_val]
        if q_val == 'funcenter_attenAge10_12':
            for val in split_val:
                funcenter_attenAge10_12.append(val)
                # funcenter_attenAge10_12 = [val for val in split_val]
        if q_val == 'funcenter_attenMuslim':
            for val in split_val:
                funcenter_attenMuslim.append(val)
                # funcenter_attenMuslim = [val for val in split_val]
        if q_val == 'funcenter_attenHindu':
            for val in split_val:
                funcenter_attenHindu.append(val)
                # funcenter_attenHindu = [val for val in split_val]
        if q_val == 'otherAct_activities':
            for val in split_val:
                otherAct_activities.append(val)
        if q_val == 'otherAct_attenMale':
            for val in split_val:
                otherAct_attenMale.append(val)
        if q_val == 'otherAct_attenFemale':
            for val in split_val:
                otherAct_attenFemale.append(val)
        if q_val == 'otherAct_attenTotal':
            for val in split_val:
                otherAct_attenTotal.append(val)
                # print funcenter_attenMuslim
                # girls group
    girls_table = get_html_table(
        get_bd_table_data("1", funcenter_boundary_list, funcenter_week, funcenter_attenAge16_17,
                          funcenter_attenAge13_15, funcenter_attenAge10_12, funcenter_attenMuslim,
                          funcenter_attenHindu), table_headers_girls)

    # boys group
    boys_table = get_html_table(get_bd_table_data("2", funcenter_boundary_list, funcenter_week, funcenter_attenAge16_17,
                                                  funcenter_attenAge13_15, funcenter_attenAge10_12,
                                                  funcenter_attenMuslim, funcenter_attenHindu), table_headers_boys)

    # activities_group
    activity_dict = {}
    for idx in range(0, len(otherAct_activities)):
        activity = int(otherAct_activities[idx])
        atten_male = int(otherAct_attenMale[idx])
        atten_female = int(otherAct_attenFemale[idx])
        atten_total = int(otherAct_attenTotal[idx])

        male_avg = round(float(atten_male) / 35, 2)
        female_avg = round(float(atten_female) / 35, 2)
        total_avg = float(male_avg) + float(female_avg)

        if activity_dict.has_key(activity):
            tmpArr = activity_dict.get(activity)
            tmpArr[0] += atten_male
            tmpArr[1] += atten_female
            tmpArr[2] += atten_total
            tmpArr[3] += male_avg
            tmpArr[4] += female_avg
            tmpArr[5] += total_avg
            activity_dict[activity] = tmpArr
        else:
            activity_dict[activity] = [atten_male, atten_female, atten_total, male_avg, female_avg, total_avg]

    for key in activity_dict:
        data_list_activities[int(key) - 1][1] = activity_dict.get(key)[0]
        data_list_activities[int(key) - 1][2] = activity_dict.get(key)[1]
        data_list_activities[int(key) - 1][3] = activity_dict.get(key)[2]
        data_list_activities[int(key) - 1][4] = activity_dict.get(key)[3]
        data_list_activities[int(key) - 1][5] = activity_dict.get(key)[4]
        data_list_activities[int(key) - 1][6] = activity_dict.get(key)[5]
    activities_table = get_html_table(data_list_activities, table_headers_activities)

    connection.close()
    if request.is_ajax():
        jsonData = {}
        jsonData[str('girls_table')] = girls_table
        jsonData[str('boys_table')] = boys_table
        jsonData[str('activities_table')] = activities_table

        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    filter_json = get_report_filters_value(request, 'bd')

    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'girls_table': girls_table,
        'boys_table': boys_table,
        'activities_table': activities_table,
        'filter_json': filter_json,
        'rpt_type': 'bd'
    })
    output = render(request, 'attendence_activity_report.html', variables);
    return HttpResponse(output)


def get_np_table_data(data_type, att_boygirl, att_week, att_16_18, att_13_15, att_10_12, att_19_24, att_d, att_b,
                      att_jj, att_m):
    data_list_group = [['week 1 avg', 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       ['week 2 avg', 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       ['week 3 avg', 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       ['week 4 avg', 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       ['week 5 avg', 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       ['Avg', 0, 0, 0, 0, 0, 0, 0, 0, 0]]
    week_dict = {}
    indices = [i for i, x in enumerate(att_boygirl) if x == data_type]
    # print 'indices'
    # print indices
    for idx in indices:
        week = att_week[idx]
        attenAge16_17 = int(att_16_18[idx])
        attenAge13_15 = int(att_13_15[idx])
        attenAge10_12 = int(att_10_12[idx])
        attenAge19_24 = int(att_19_24[idx])
        attenDalit = int(att_d[idx])
        attenBrahmin = int(att_b[idx])
        attenJanajati = int(att_jj[idx])
        attenMuslim = int(att_m[idx])
        weekly_avg = (attenAge16_17 + attenAge13_15 + attenAge10_12 + attenAge19_24) / 4
        if week_dict.has_key(week):
            data_list = week_dict.get(week)

            data_list[0] += attenAge10_12
            # print 'data_list: '+ 'attenAge10_12'
            # print str(data_list[0]) + ' '+str(attenAge10_12)
            data_list[1] += attenAge13_15
            data_list[2] += attenAge16_17
            data_list[3] += attenAge19_24
            data_list[4] += weekly_avg
            data_list[5] += attenDalit
            data_list[6] += attenBrahmin
            data_list[7] += attenJanajati
            data_list[8] += attenMuslim
            # print 'data_list'+ 'week: '+week
            # print data_list
            week_dict[week] = data_list
        else:
            week_dict[week] = [attenAge10_12, attenAge13_15, attenAge16_17, attenAge19_24, weekly_avg, attenDalit,
                               attenBrahmin, attenJanajati, attenMuslim]

        for week in week_dict.keys():
            data_list_group[int(week) - 1][1] = week_dict.get(week)[0]
            data_list_group[int(week) - 1][2] = week_dict.get(week)[1]
            data_list_group[int(week) - 1][3] = week_dict.get(week)[2]
            data_list_group[int(week) - 1][4] = week_dict.get(week)[3]
            data_list_group[int(week) - 1][5] = week_dict.get(week)[4]
            data_list_group[int(week) - 1][6] = week_dict.get(week)[5]
            data_list_group[int(week) - 1][7] = week_dict.get(week)[6]
            data_list_group[int(week) - 1][8] = week_dict.get(week)[7]
            data_list_group[int(week) - 1][9] = week_dict.get(week)[8]

        for index in range(1, 10):
            sum_data = 0
            for idx in range(0, 5):
                # print data_list_group[idx][index]
                sum_data += int(data_list_group[idx][index])
            data_list_group[5][index] = sum_data / 5
    return data_list_group


def get_bd_table_data(data_type, f_boundary, f_week, f_att_1617, f_att_1315, f_att_1012, f_att_m, f_att_h):
    data_list_group = [['week 1 avg', '0', '0', '0', '0', '0', '0'],
                       ['week 2 avg', '0', '0', '0', '0', '0', '0'],
                       ['week 3 avg', '0', '0', '0', '0', '0', '0'],
                       ['week 4 avg', '0', '0', '0', '0', '0', '0'],
                       ['week 5 avg', '0', '0', '0', '0', '0', '0'],
                       ['Avg', '', '', '', '', '', '']]
    week_dict = {}
    indices = [i for i, x in enumerate(f_boundary) if x == data_type]
    # print 'indices'
    # print indices
    for idx in indices:
        # print idx
        week = f_week[idx]
        attenAge16_17 = int(f_att_1617[idx])
        attenAge13_15 = int(f_att_1315[idx])
        attenAge10_12 = int(f_att_1012[idx])
        try:
            attenMuslim = int(f_att_m[idx])
        except Exception, e:
            print
            f_att_m
            print
            idx
            continue
        weekly_avg = float(attenAge16_17 + attenAge13_15 + attenAge10_12) / 3
        attenHindu = int(f_att_h[idx])
        attenMuslim = int(f_att_m[idx])
        if week_dict.has_key(week):
            data_list = week_dict.get(week)

            data_list[0] += attenAge10_12
            # print 'data_list: '+ 'attenAge10_12'
            # print str(data_list[0]) + ' '+str(attenAge10_12)
            data_list[1] += attenAge13_15
            data_list[2] += attenAge16_17
            data_list[3] += weekly_avg
            data_list[4] += attenHindu
            data_list[5] += attenMuslim
            # print 'data_list'+ 'week: '+week
            # print data_list
            week_dict[week] = data_list
        else:
            week_dict[week] = [attenAge10_12, attenAge13_15, attenAge16_17, weekly_avg, attenHindu, attenMuslim]

        for week in week_dict.keys():
            data_list_group[int(week) - 1][1] = week_dict.get(week)[0]
            data_list_group[int(week) - 1][2] = week_dict.get(week)[1]
            data_list_group[int(week) - 1][3] = week_dict.get(week)[2]
            data_list_group[int(week) - 1][4] = week_dict.get(week)[3]
            data_list_group[int(week) - 1][5] = week_dict.get(week)[4]
            data_list_group[int(week) - 1][6] = week_dict.get(week)[5]

        for index in range(1, 7):
            sum_data = 0
            for idx in range(0, 5):
                # print data_list_group[idx][index]
                sum_data += float(data_list_group[idx][index])
            data_list_group[5][index] = float(sum_data / 5)
    return data_list_group


def get_report_bd_girl_boy_status_change(request):
    status_list = ['dummy', 'Unmarried to married', 'School Re-enrollment', 'School Dropout', 'IGA involvement',
                   'Others']
    table_headers_stat_change = ['Fun Center Name', 'Boys/girls Name', 'Age', 'Change Status']
    col_width = ['30%', '25%', '25%', '25%']
    data_list_stat_change = []

    pngo_name = '%'
    vdc_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    status = '%'
    start_date = '2000-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        status = request.POST.get('status')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    main_query = "with p as(with t as( select logger_instance.id ID, xform_id, user_id,(select username from auth_user where id=logger_instance.user_id) username ,to_char((logger_instance.json->>'profile/month')::date,'DD Mon YYYY') Received,(case when (logger_instance.json->>'profile/month')::date is null then date_created else (logger_instance.json->>'profile/month')::date end) date_created,logger_instance.json->>'profile/adoName' ado_name,logger_instance.json->>'profile/age' age,unnest(string_to_array((logger_instance.json->>'profile/changeStatus')::text,' ')) changestatus,logger_instance.json->>'profile/upazila' upazila,logger_instance.json->>'profile/union' _union,logger_instance.json->>'profile/village' village,logger_instance.json->>'profile/pngo' pngo from logger_instance where deleted_at is null and xform_id=249 and (logger_instance.json->>'profile/changeStatus')::text is not null) select village,ado_name,age,(case changestatus when '1' then 'Unmarried to married' when '2' then 'School Re-enrollment' when '3' then 'School Dropout' when '4' then 'IGA involvement' when '5' then 'Others' else '' end) changestatus from t where date_created between '" + start_date + "' and '" + end_date + "' and upazila like '" + upzilla_name + "' and _union like '" + union_name + "' and village like '" + village_name + "' and pngo like '" + pngo_name + "') select village,ado_name,age,string_agg(changestatus, ', ' order by changestatus) from p group by village,ado_name,age"

    full_query = main_query
    cursor = connection.cursor()
    cursor.execute(full_query)
    db_ret_value = cursor.fetchall()
    # print db_ret_value
    inst_id = 0
    count = 0
    data_list = [0, 0, 0, 0]
    # print 'db_ret_value'
    # print db_ret_value
    for each in db_ret_value:
        g_b_age = 0
        g_b_Name = ''
        g_b_fun_center = ''
        g_b_status = ''
        data_list[0] = str(each[0])
        data_list[1] = str(each[1])
        data_list[2] = str(each[2])
        data_list[3] = str(each[3])
        data_list_stat_change.append(data_list)
        data_list = [0, 0, 0, 0]

    chng_stat_table = get_html_table(data_list_stat_change, table_headers_stat_change, col_width)
    results = None
    try:
        main_query = "with p as(with t as( select logger_instance.id ID, xform_id, user_id,(select username from auth_user where id=logger_instance.user_id) username ,to_char((logger_instance.json->>'profile/month')::date,'DD Mon YYYY') Received,(case when (logger_instance.json->>'profile/month')::date is null then date_created else (logger_instance.json->>'profile/month')::date end) date_created,logger_instance.json->>'profile/adoName' ado_name,logger_instance.json->>'profile/age' age,unnest(string_to_array((logger_instance.json->>'profile/changeStatus')::text,' ')) changestatus,logger_instance.json->>'profile/upazila' upazila,logger_instance.json->>'profile/union' _union,logger_instance.json->>'profile/village' village,logger_instance.json->>'profile/pngo' pngo from logger_instance where deleted_at is null and xform_id=249 and (logger_instance.json->>'profile/changeStatus')::text is not null) select village,ado_name,age,changestatus from t where date_created between '" + start_date + "' and '" + end_date + "' and upazila like '" + upzilla_name + "' and _union like '" + union_name + "' and village like '" + village_name + "' and pngo like '" + pngo_name + "') select changestatus, count(*) from p group by changestatus"

        print
        main_query
        cursor.execute(main_query)
        results = cursor.fetchall()
        print
        results

    except Exception as e:
        print
        e
        connection._rollback()
    finally:
        cursor.close()

    status_chart_data = {}
    if results is not None:
        for every in results:
            if str(every[0]) == '1':
                status_chart_data['unm_to_marr'] = int(every[1])
            if str(every[0]) == '2':
                status_chart_data['s_re_enrol'] = int(every[1])
            if str(every[0]) == '3':
                status_chart_data['sch_drop'] = int(every[1])
            if str(every[0]) == '4':
                status_chart_data['iga_inv'] = int(every[1])
            if str(every[0]) == '5':
                status_chart_data['oth'] = int(every[1])

    # status_chart_data['unm_to_marr'] = int(results[0])
    # status_chart_data['s_re_enrol'] = int(results[1])
    # status_chart_data['sch_drop'] = int(results[2])
    # status_chart_data['iga_inv'] = int(results[3])
    # status_chart_data['oth'] = int(results[4])

    print
    status_chart_data

    if request.is_ajax():
        jsonData = {}
        jsonData[str('chng_stat_table')] = chng_stat_table
        jsonData[str('status_chart_data')] = status_chart_data
        jsonData[str('rpt_type')] = 'bd'
        return HttpResponse(json.dumps(jsonData), content_type='application/json');
    filter_json = get_report_filters_value(request, 'bd')
    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'chng_stat_table': chng_stat_table,
        'status_chart_data': status_chart_data,
        'filter_json': filter_json,
        'rpt_type': 'bd',
    })
    output = render(request, 'g_b_status_change_report.html', variables);
    return HttpResponse(output)


def get_report_np_girl_boy_status_change(request):
    status_list = ['Unmarried', 'Married but no Gouna',
                   'Married with Gouna (Daughter/Son)''Married with Gouna (Daughter-in-law)', 'Other']
    table_headers_stat_change = ['Fun Center Name', 'Boys/girls Name', 'Age', 'Sex', 'Change Status']
    col_width = ['25%', '20%', '20%', '20%', '35%']
    data_list_stat_change = []

    pngo_name = '%'
    vdc_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    status = '%'
    start_date = '2000-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        status = request.POST.get('status')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    main_query = "with p as(with t as( select logger_instance.id ID, xform_id, user_id,(select username from auth_user where id=logger_instance.user_id) username ,to_char((logger_instance.json->>'profile/date')::date,'DD Mon YYYY') Received,(case when(logger_instance.json->>'profile/date')::date is null then date_created::date else (logger_instance.json->>'profile/date')::date end) date_created,logger_instance.json->>'detail/adoName' ado_name,logger_instance.json->>'detail/age' age,logger_instance.json->>'detail/sex' sex,unnest(string_to_array((logger_instance.json->>'detail/statusChange')::text,' ')) changestatus,logger_instance.json->>'profile/vdc' village,logger_instance.json->>'profile/pngo' pngo from logger_instance where deleted_at is null and xform_id=321 and (logger_instance.json->>'detail/statusChange')::text is not null) select village,ado_name,age,sex,(case changestatus when '1' then 'Unmarried' when '2' then 'Married but no Gouna' when '3' then 'Married with Gouna (Daughter/Son)' when '4' then 'Married with Gouna (Daughter-in-law)' when '5' then 'Other' end) changestatus from t where date_created between '" + start_date + "' and '" + end_date + "' and village like '" + village_name + "' and pngo like '" + pngo_name + "') select village,ado_name,age,(case sex when '1' then 'Girl' else 'Boy' end) sex,string_agg(changestatus, ', ' order by changestatus) from p group by village,ado_name,age,sex"
    print
    main_query
    full_query = main_query
    cursor = connection.cursor()
    cursor.execute(full_query)
    db_ret_value = cursor.fetchall()
    # print db_ret_value
    inst_id = 0
    count = 0
    data_list = [0, 0, 0, 0, 0]
    # print 'db_ret_value'
    # print db_ret_value
    for each in db_ret_value:
        g_b_age = 0
        g_b_Name = ''
        g_b_fun_center = ''
        g_b_status = ''
        data_list[0] = str(each[0])
        data_list[1] = str(each[1])
        data_list[2] = str(each[2])
        data_list[3] = str(each[3])
        data_list[4] = str(each[4])
        data_list_stat_change.append(data_list)
        data_list = [0, 0, 0, 0, 0]

    chng_stat_table = get_html_table(data_list_stat_change, table_headers_stat_change, col_width)

    results = None
    try:
        main_query = "with p as(with t as(select logger_instance.id ID, xform_id, user_id,(select username from auth_user where id=logger_instance.user_id) username ,to_char((logger_instance.json->>'profile/date')::date,'DD Mon YYYY') Received,(case when (logger_instance.json->>'profile/date')::date is null then date_created::date else (logger_instance.json->>'profile/date')::date end) date_created,logger_instance.json->>'detail/adoName' ado_name,logger_instance.json->>'detail/age' age,unnest(string_to_array((logger_instance.json->>'detail/statusChange')::text,' ')) changestatus,logger_instance.json->>'profile/vdc' village,logger_instance.json->>'profile/pngo' pngo from logger_instance where deleted_at is null and xform_id=321 and (logger_instance.json->>'detail/statusChange')::text is not null) select village,ado_name,age,changestatus from t where date_created between '" + start_date + "' and '" + end_date + "' and village like '" + village_name + "' and pngo like '" + pngo_name + "') select changestatus, count(*) from p group by changestatus"

        cursor.execute(main_query)
        results = cursor.fetchall()

    except Exception as e:
        print
        e
        connection._rollback()
    finally:
        cursor.close()

    status_chart_data = {}
    if results is not None:
        for every in results:
            if str(every[0]) == '1':
                status_chart_data['unm_to_marr'] = int(every[1])
            if str(every[0]) == '2':
                status_chart_data['s_re_enrol'] = int(every[1])
            if str(every[0]) == '3':
                status_chart_data['sch_drop'] = int(every[1])
            if str(every[0]) == '4':
                status_chart_data['iga_inv'] = int(every[1])
            if str(every[0]) == '5':
                status_chart_data['oth'] = int(every[1])

                # print status_chart_data

    if request.is_ajax():
        jsonData = {}
        jsonData[str('chng_stat_table')] = chng_stat_table
        jsonData[str('status_chart_data')] = status_chart_data
        jsonData[str('rpt_type')] = 'np'
        return HttpResponse(json.dumps(jsonData), content_type='application/json')
    filter_json = get_report_filters_value(request, 'np')
    variables = RequestContext(request, {
        'head_title': 'Project Summary',
        'chng_stat_table': chng_stat_table,
        'status_chart_data': status_chart_data,
        'filter_json': filter_json,
        'rpt_type': 'np',
    })
    output = render(request, 'g_b_status_change_report.html', variables)
    return HttpResponse(output)


def get_report_bd_staff_transformation(request):
    table_headers_staff_trans = ['ID', 'Month', 'Fun Center Name', 'CF', 'CV', 'Details']
    col_width = ['20%', '20%', '20%', '20%', '20%']
    qry = ""

    data_list_staff_trans = []

    pngo_name = '%'
    vdc_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

    cursor = connection.cursor()
    try:
        qry = "with t as( select id,row_number()over ( order by id) sl,(json->>'geo/month')::date date_created, json->>'geo/pngo' pngo,json->>'geo/upazila' upazila,json->>'geo/union' _union, json->>'geo/village' village,json->>'cfTransformation' cftransform,json->>'cfChanges' cfchange, json->>'cvTransformation' cvtransform, json->>'cvChanges' cvchange from vwapprovedlogger_instance where xform_id=272) select id,sl,date_created,village,cftransform,cfchange,cvtransform,cvchange from t where date_created between '" + start_date + "' and '" + end_date + "' and upazila like '" + upzilla_name + "' and _union like '" + union_name + "' and village like '" + village_name + "' and pngo like '" + pngo_name + "'"
        cursor.execute(qry)
        results = cursor.fetchall()
        row_count = cursor.rowcount

    finally:
        cursor.close()

    curr_inst_id = 0
    count = 0
    tb_data_list = None

    tb_data_dict = {}
    row_data_dict = {}
    # [1098, '2017-02-01', 'Gopalpur', 'No', 'No', '<button class="btn" id="17566" type="button" onclick="pop_details()">Details</button>']
    for each in results:
        # print each[3]
        tb_data_list = [None, None, None, None, None, None]
        tb_data_list[0] = str(each[1])
        tb_data_list[1] = str(each[2])
        tb_data_list[2] = str(each[3])
        tb_data_list[3] = 'Yes' if str(each[4]) == '1' else 'No'
        tb_data_list[4] = 'Yes' if str(each[6]) == '1' else 'No'
        tb_data_list[5] = '<button class="btn" id="' + str(each[0]) + '" type="button" onclick="">Details</button>'
        data_list_staff_trans.append(tb_data_list)
        tb_data_list = [None, None, None, None, None, None]

        if str(each[4]) == '1':
            row_data_dict['cfChanges'] = (each[5].encode('utf-8'))
        row_data_dict['cvTransformation'] = str(each[4])
        if str(each[6]) == '1':
            row_data_dict['cvChanges'] = (each[7].encode('utf-8'))
        row_data_dict['cfTransformation'] = str(each[6])
        row_data_dict['geo_village'] = str(each[3])
        row_data_dict['geo_month'] = str(each[2])
        tb_data_dict[str(each[0])] = row_data_dict
        row_data_dict = {}

        # print tb_data_dict
    staff_trans_table = get_html_table(data_list_staff_trans, table_headers_staff_trans, col_width)

    cursor = connection.cursor()
    try:
        qry = "with p as(with t as( select (json->>'geo/month')::date date_created, json->>'geo/pngo' pngo,json->>'geo/upazila' upazila,json->>'geo/union' _union, json->>'geo/village' village,json->>'cfTransformation' cftransform,json->>'cvTransformation' cvtransform from vwapprovedlogger_instance where xform_id=272) select (case cftransform when '1' then 1 else 0 end) cf_yes,(case cftransform when '2' then 1 else 0 end) cf_no,(case cvtransform when '1' then 1 else 0 end) cv_yes,(case cvtransform when '2' then 1 else 0 end) cv_no from t where date_created between '" + start_date + "' and '" + end_date + "' and upazila like '" + upzilla_name + "' and _union like '" + union_name + "' and village like '" + village_name + "' and pngo like '" + pngo_name + "') select sum(cf_yes) cf_yes,sum(cf_no) cf_no,sum(cv_yes) cv_yes,sum(cv_no) cv_no from p"
        cursor.execute(qry)
        chart_db_value = cursor.fetchone()
    finally:
        cursor.close()

    # print chart_db_value
    trans_chart_data = {}
    trans_chart_data['cf_yes'] = int(chart_db_value[0])
    trans_chart_data['cf_no'] = int(chart_db_value[1])
    trans_chart_data['cv_yes'] = int(chart_db_value[2])
    trans_chart_data['cv_no'] = int(chart_db_value[3])

    if request.is_ajax():
        jsonData = {}
        jsonData[str('staff_trans_table')] = staff_trans_table
        jsonData[str('trans_chart_data')] = trans_chart_data
        jsonData[str('tb_data_dict')] = tb_data_dict
        return HttpResponse(json.dumps(jsonData), content_type='application/json');
    filter_json = get_report_filters_value(request, 'bd')
    variables = RequestContext(request, {
        'staff_trans_table': staff_trans_table,
        'trans_chart_data': trans_chart_data,
        'tb_data_dict': json.dumps(tb_data_dict),
        'filter_json': filter_json,
        'rpt_type': 'bd',
    })
    output = render(request, 'staff_transformation_report.html', variables);
    return HttpResponse(output)


def get_report_bd_obsrv_jrnal(request):
    pngo_name = '%'
    vdc_name = '%'
    upzilla_name = '%'
    union_name = '%'
    village_name = '%'
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    filter_json = get_report_filters_value(request, 'bd')

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        upzilla_name = request.POST.get('upzilla')
        union_name = request.POST.get('union')
        village_name = request.POST.get('village')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
    # print pngo_name
    cursor = connection.cursor()
    try:
        cursor.execute("BEGIN")
        cursor.callproc("get_care_bd_ff_obsrv_data",
                        [pngo_name, upzilla_name, union_name, village_name, start_date, end_date])
        db_return = cursor.fetchall()
        row_count = cursor.rowcount
        cursor.execute("COMMIT")
    finally:
        cursor.close()
    # print db_return
    # final data creation array
    chng_bound_part_name = ['dummy', 'girls', 'boys', 'mothers', 'fathers', 'role_m', 'evw_forum', 'cv', 'cf', 'other']
    chng_bound_part_count = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    chng_exp_unexp_count = [0, 0, 0]
    chng_major_minor_count = [0, 0, 0, 0]
    chng_pos_neg_count = [0, 0, 0]
    # end of final data creation array

    chng_bound_part = []
    chng_exp_unexp = []
    chng_major_minor = []
    chng_pos_neg = []
    chng_union = []
    chng_village = []

    for each_row in db_return:
        ques_name = str(each_row[1])
        if ques_name == 'change_boundaryPart':
            chng_bound_part.append(int(each_row[2]))
        if ques_name == 'change_ExpectUnexpect':
            chng_exp_unexp.append(int(each_row[2]))
        if ques_name == 'change_MajorMinor':
            chng_major_minor.append(int(each_row[2]))
        if ques_name == 'change_PositiveNegative':
            chng_pos_neg.append(int(each_row[2]))
        if ques_name == 'change_union':
            chng_union.append(str(each_row[2]))
        if ques_name == 'change_village':
            chng_village.append(str(each_row[2]))

    data_to_send = {}

    if union_name != '%':

        tmp_chng_exp_unexp = []
        tmp_chng_major_minor = []
        tmp_chng_pos_neg = []

        for idx in range(len(chng_bound_part)):
            chng_bound_part_count[chng_bound_part[idx]] += 1
        indices = [i for i, x in enumerate(chng_union) if x == union_name]

        for idx in indices:
            tmp_chng_exp_unexp.append(chng_exp_unexp[idx])
            tmp_chng_major_minor.append(chng_major_minor[idx])
            tmp_chng_pos_neg.append(chng_pos_neg[idx])
        data_to_send = __get_bd_obsrv_data_dict(tmp_chng_major_minor, tmp_chng_pos_neg, tmp_chng_exp_unexp,
                                                chng_bound_part)

    else:
        data_to_send = __get_bd_obsrv_data_dict(chng_major_minor, chng_pos_neg, chng_exp_unexp, chng_bound_part)
    print
    data_to_send

    if request.is_ajax():
        jsonData = {}
        jsonData[str('data_dict')] = data_to_send
        return HttpResponse(json.dumps(jsonData), content_type='application/json');

    variables = RequestContext(request, {
        'rpt_type': 'bd',
        'filter_json': filter_json,
        'data_dict': json.dumps(data_to_send),
    })
    output = render(request, 'obsrv_journal_report.html', variables);
    return HttpResponse(output)


def __get_bd_obsrv_data_dict(chng_major_minor, chng_pos_neg, chng_exp_unexp, chng_bound_part):
    chng_bound_part_name = ['dummy', 'girls', 'boys', 'mothers', 'fathers', 'role_m', 'evw_forum', 'cv', 'cf', 'other']
    data_dict = {}
    chng_bound_part_count = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    chng_exp_unexp_count = [0, 0, 0]
    chng_pos_neg_count = [0, 0, 0]
    pos_exp_unexp = [0, 0]
    neg_exp_unexp = [0, 0]

    for idx in range(len(chng_bound_part)):
        chng_bound_part_count[chng_bound_part[idx]] += 1

    indices_major = [i for i, x in enumerate(chng_major_minor) if x == 1]
    indices_minor = [i for i, x in enumerate(chng_major_minor) if x == 2]
    indices_imp = [i for i, x in enumerate(chng_major_minor) if x == 3]

    for each in indices_major:

        chng_pos_neg_count[chng_pos_neg[each]] += 1
        if chng_pos_neg[each] == 1:
            pos_exp_unexp[chng_exp_unexp[each] - 1] += 1
        else:
            neg_exp_unexp[chng_exp_unexp[each] - 1] += 1
        # chng_exp_unexp_count[chng_exp_unexp[each]] += 1
    else:
        data_dict['major_chng_total'] = len(indices_major)
        data_dict['major_pos_neg'] = chng_pos_neg_count
        data_dict['major_pos_exp_unexp'] = pos_exp_unexp
        data_dict['major_neg_exp_unexp'] = neg_exp_unexp

    chng_exp_unexp_count = [0, 0, 0]
    chng_pos_neg_count = [0, 0, 0]
    pos_exp_unexp = [0, 0]
    neg_exp_unexp = [0, 0]

    for each in indices_minor:
        chng_pos_neg_count[chng_pos_neg[each]] += 1
        if chng_pos_neg[each] == 1:
            pos_exp_unexp[chng_exp_unexp[each] - 1] += 1
        else:
            neg_exp_unexp[chng_exp_unexp[each] - 1] += 1
    else:
        data_dict['minor_chng_total'] = len(indices_minor)
        data_dict['minor_pos_neg'] = chng_pos_neg_count
        data_dict['minor_pos_exp_unexp'] = pos_exp_unexp
        data_dict['minor_neg_exp_unexp'] = neg_exp_unexp

    chng_exp_unexp_count = [0, 0, 0]
    chng_pos_neg_count = [0, 0, 0]
    pos_exp_unexp = [0, 0]
    neg_exp_unexp = [0, 0]

    for each in indices_imp:
        chng_pos_neg_count[chng_pos_neg[each]] += 1
        if chng_pos_neg[each] == 1:
            pos_exp_unexp[chng_exp_unexp[each] - 1] += 1
        else:
            neg_exp_unexp[chng_exp_unexp[each] - 1] += 1
    else:
        data_dict['imp_chng_total'] = len(indices_imp)
        data_dict['imp_pos_neg'] = chng_pos_neg_count
        data_dict['imp_pos_exp_unexp'] = pos_exp_unexp
        data_dict['imp_neg_exp_unexp'] = neg_exp_unexp

    for i in range(len(chng_bound_part_name)):
        data_dict[chng_bound_part_name[i]] = chng_bound_part_count[i]

    return data_dict


def get_html_table(data_list, table_headers=None, column_width=None):
    if column_width is None:
        htmlcode = HTML.table(data_list, header_row=table_headers,
                              col_width=['20%', '15%', '15%', '15%', '15%', '15%', '20%'])
    else:
        htmlcode = HTML.table(data_list, header_row=table_headers, col_width=column_width)
    return_html = str(htmlcode).replace('<TABLE', '<TABLE class="sortable" id="sortable"')
    return return_html


def get_report_filters_value(request, rpt_type):
    if rpt_type == 'bd':
        asd_union_village_dict = {}
        asd_upzilla_union_dict = {}
        pngo_upzilla_dict = {}

        # ASD
        bhatipara_village_list = ['Dattagram', 'Dhalkutub', 'Kuchir gaon', 'Mothurapur']
        chamarchar_village_list = ['Chamarchar', 'Kamalpur', 'Kartikpur', 'Lowlarchar', 'Perua', 'Shamarchar']
        deraisaromangal_village_list = ['Chitolia', 'Chondipur', 'Nachni', 'Saromangal']
        jogdol_village_list = ['Kambribij', 'Nurpur', 'Sarongpasha']
        kulanj_village_list = ['Dokshin Suriar Par', 'Tetoya', 'Uttar Suriarpar']
        rofinagar_village_list = ['Khagaura', 'Mirjapur', 'Sechni']
        tarol_village_list = ['Amirpur', 'Bawshi', 'Islampur', 'Kadirpur', 'Vhangador']

        asd_union_village_dict['Bhatipara'] = bhatipara_village_list
        asd_union_village_dict['Chamarchar'] = chamarchar_village_list
        asd_union_village_dict['Derai Saromangal'] = deraisaromangal_village_list
        asd_union_village_dict['Jogdol'] = jogdol_village_list
        asd_union_village_dict['Kulanj'] = kulanj_village_list
        asd_union_village_dict['Rofinagar'] = rofinagar_village_list
        asd_union_village_dict['Tarol'] = tarol_village_list

        asd_upzilla_union_dict['Derai'] = asd_union_village_dict

        asd_union_village_dict = {}

        dohalia_village_list = ['Hazi Nagar menda', 'Noagaon', 'Panail', 'Shibpur']
        mannargaon_village_list = ['Aminpur', 'Karimpur', 'Mannargoan', 'Rampur']
        pandargaon_village_list = ['Gopi Nogor', 'Notun Krishnonagor', 'Polirchar', 'Sonapur']

        asd_union_village_dict['Dohalia'] = dohalia_village_list
        asd_union_village_dict['Mannargaon'] = mannargaon_village_list
        asd_union_village_dict['Pandargaon'] = pandargaon_village_list

        asd_upzilla_union_dict['Doarabazar'] = asd_union_village_dict
        pngo_upzilla_dict['ASD'] = asd_upzilla_union_dict

        # END OF ASD


        # JASHIS

        beheli_village_list = ['Bagani', 'Bahali Alipur', 'Gopalpur', 'Gossho Gram', 'Horinagar', 'Islampur',
                               'Notun Moshalgat', 'Putia', 'Shibpur']
        fenarback_village_list = ['Posim Fenarbak', 'Sarifpur', 'Dokkin Laxmipur', 'Enatnagar', 'Josmontopur',
                                  'Krisnopur', 'Saydnogor', 'Shukdebpur', 'Uttar LaxmiPur']
        jamalganj_sadar_village_list = ['Batal Alipur', 'Chanpur -2', 'Golerhati', 'Hinhu Kalipur', 'Insanpur',
                                        'Junupur', 'KaminiPur', 'Masumpur', 'NoyaHalot', 'Sharthpur', 'Vuhyer hati']
        sachnabazar_village_list = ['Akthapara', 'Bramongaun', 'Chanpur -1', 'Fazilpur', 'Horipur', 'Kanda goan',
                                    'Kukraporshi', 'Mofij Nogor', 'Polockpur', 'Polok', 'Radanager', 'Shorifpur']
        vimkhali_village_list = ['Chandar Nagar', 'Fekulmahamudpur', 'Gazipur', 'Hararkandi', 'KalKatkha', 'Kamlabaz',
                                 'Mollikpur', 'Teranagor', 'Vanda']

        # jashis_union_village_dict = {}
        jashis_upzilla_union_dict = {}

        jashis_union_village_dict = {}

        jashis_union_village_dict['Beheli'] = beheli_village_list
        jashis_union_village_dict['Fenarback'] = fenarback_village_list
        jashis_union_village_dict['Jamalgonj Sadar'] = jamalganj_sadar_village_list
        jashis_union_village_dict['Sachnabazar'] = sachnabazar_village_list
        jashis_union_village_dict['Vimkhali'] = vimkhali_village_list

        jashis_upzilla_union_dict['Jamalganj'] = jashis_union_village_dict

        pngo_upzilla_dict['JASHIS'] = jashis_upzilla_union_dict

        return json.dumps(pngo_upzilla_dict)
    if rpt_type == 'np':
        pngo_vdc_dict = {}
        dsdc_vdc_list = ['Baluhawa', 'Ajigara', 'Bashkhor', 'Gotihawa', 'Harnampur', 'Pursottampur', 'Sihokhor',
                         'Somdih']
        sss_vdc_list = ['Bairghat', 'Chhotkiramnagar', 'Ekala', 'Maryadpur', 'Raypur', 'Semara', 'Tenuhawa',
                        'Thu. Piprahawa']
        pngo_vdc_dict['DSDC'] = dsdc_vdc_list
        pngo_vdc_dict['SSS'] = sss_vdc_list

        return json.dumps(pngo_vdc_dict)
    return 0


def get_report_pentaho(request):
    variables = RequestContext(request, {
        'head_title': 'Project Summary',
    })
    output = render(request, 'test_pentaho_report.html', variables);
    return HttpResponse(output)


def observation_journal(request):
    fdcs_query = "with q as( with t as( SELECT json->>'geo/pngo' tmp_pngo, json_array_elements((json->>'change')::json) change FROM public.vwapprovedlogger_instance where xform_id=252 and(json->>'geo/month')::Date between '1-1-2016' and '1-1-2017') select change->>'change/boundaryPart' boundar_part from t) select (case boundar_part when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers (FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end) boundar_part,count(*) from q group by boundar_part"
    fdcs_data = json.dumps(__db_fetch_values_dict(fdcs_query))

    filter_json = get_report_filters_value(request, 'bd')

    variables = RequestContext(request, {
        'rpt_type': 'bd',
        'fdcs_data': fdcs_data,
        'filter_json': filter_json
    })
    return render(request, 'observation_journal_new.html', variables)


def np_observation_journal(request):
    pngo_name = '%'
    vdc_name = '%'
    is_export = False
    start_date = '2016-01-01'
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if request.is_ajax():
        pngo_name = request.POST.get('pngo')
        if pngo_name is None or pngo_name   =='':
            pngo_name = '%'
        vdc_name = request.POST.get('village')
        if vdc_name is None or vdc_name=='':
            vdc_name = '%'
        start_date = request.POST.get('start_date')
        if start_date is None or start_date=='':
            start_date = '2016-01-01'
        end_date = request.POST.get('end_date')
        if end_date is None or end_date =='':
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        is_export = request.POST.get('is_export')
        if is_export is None:
            is_export = False
        fdcs_query = "with q as( with t as( SELECT json->>'basic/pngo' tmp_pngo,json->>'basic/vdc' tmp_vdc, json_array_elements((json->>'change')::json) change FROM public.vwapprovedlogger_instance where xform_id=305 and(json->>'basic/month')::Date between '" + str(
            start_date) + "' and '" + str(
            end_date) + "') select change->>'change/boundaryPart' boundar_part from t where tmp_pngo like '" + str(
            pngo_name) + "' and tmp_vdc like '" + str(
            vdc_name) + "') select (CASE boundar_part WHEN '10' THEN 'Girl group' WHEN '11' THEN 'Boy group' WHEN '12' THEN 'Mother group' WHEN '13' THEN 'Father group' WHEN '14' THEN 'SMC' WHEN '15' THEN 'Religious groups' WHEN '16' THEN 'Local Government' END) boundar_part,count(*) from q where boundar_part::int>9 group by boundar_part order by boundar_part"
        fdcs_data = json.dumps(__db_fetch_values_dict(fdcs_query))
        print(fdcs_data)
        return HttpResponse(fdcs_data)





    fdcs_query = "with q as( with t as( SELECT json->>'basic/pngo' tmp_pngo,json->>'basic/vdc' tmp_vdc, json_array_elements((json->>'change')::json) change FROM public.vwapprovedlogger_instance where xform_id=305 and(json->>'basic/month')::Date between '" +str(start_date) + "' and '" + str(end_date) + "') select change->>'change/boundaryPart' boundar_part from t where tmp_pngo like '" +str( pngo_name )+ "' and tmp_vdc like '" +str( vdc_name) + "') select (CASE boundar_part WHEN '10' THEN 'Girl group' WHEN '11' THEN 'Boy group' WHEN '12' THEN 'Mother group' WHEN '13' THEN 'Father group' WHEN '14' THEN 'SMC' WHEN '15' THEN 'Religious groups' WHEN '16' THEN 'Local Government' END) boundar_part,count(*) from q where boundar_part::int>9 group by boundar_part order by boundar_part"

    # print fdcs_query
    fdcs_data = json.dumps(__db_fetch_values_dict(fdcs_query))
    filter_json = get_report_filters_value(request, 'np')

    variables = RequestContext(request, {
        'rpt_type': 'np',
        'fdcs_data': fdcs_data,
        'filter_json': filter_json
    })
    return render(request, 'np_observation_journal_new.html', variables)


def bd_obsrv_jrnal_toc(request):
    change_query = "select id,id_string from logger_xform order by id_string; with q as( with t as( SELECT json->>'geo/pngo' tmp_pngo, json_array_elements((json->>'change')::json) change FROM public.vwapprovedlogger_instance where xform_id=252 and(json->>'geo/month')::Date between '1-1-2016' and '1-1-2017') select 'contribuTP' change_type,change->>'change/contribuTP' val, (case change->>'change/contribuTP' when '1' then '0_20' when '2' then '40_60' when '3' then '80_100' end) txt from t union all select 'MajorMinor' change_type,change->>'change/MajorMinor' val, (case change->>'change/MajorMinor' when '1' then 'Major' when '2' then 'Minor' when '3' then 'Important' end) txt from t union all select 'PositiveNegative' change_type,change->>'change/PositiveNegative' val, (case change->>'change/PositiveNegative' when '1' then 'Positive' when '2' then 'Negative' end) txt from t union all select 'ExpectUnexpect' change_type,change->>'change/ExpectUnexpect' val, (case change->>'change/ExpectUnexpect' when '1' then 'Expected' when '2' then 'Unexpected' end) txt from t) select change_type,val,txt,count(*) frq from q group by change_type,val,txt order by 1,2"
    change_data = json.dumps(__db_fetch_values_dict(change_query))

    unexpected_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal) select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/ExpectUnexpect' val,unnest(string_to_array(change->>'change/village',' '))village from t) select _union,bp,village,val,(select village_type from village_typedef where village=q.village) vill_type,count(*) frq from q group by village,val,_union,bp ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers(FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    unexpected_chart_data = json.dumps(__db_fetch_values_dict(unexpected_chart_query), default=decimal_default)

    positive_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal) select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/PositiveNegative' val,unnest(string_to_array(change->>'change/village',' '))village from t) select _union,bp,village,val,(select village_type from village_typedef where village=q.village) vill_type,count(*) frq from q group by village,val,_union,bp ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers(FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    positive_chart_data = json.dumps(__db_fetch_values_dict(positive_chart_query), default=decimal_default)

    majorminor_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal) select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/MajorMinor' val,unnest(string_to_array(change->>'change/village',' '))village from t) select _union,bp,village,val,(select village_type from village_typedef where village=q.village) village_type,count(*) frq from q group by village,val,_union,bp ) select bp,( CASE bp WHEN '1' THEN 'Fun center Girls-BP1' WHEN '2' THEN 'Fun center Boys-BP2' WHEN '3' THEN 'Mothers(FC adolescent) -BP3' WHEN '4' THEN 'Fathers(FC Adolescent) -BP4' WHEN '5' THEN 'EVAW Forum -BP5' WHEN '6' THEN 'Role Model -BP6' WHEN '7' THEN 'CV-BP7' WHEN '8' THEN 'CF-BP8' WHEN '9' THEN 'Others-FF-BP9' END )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    majorminor_chart_data = json.dumps(__db_fetch_values_dict(majorminor_chart_query), default=decimal_default)

    contrib_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal) select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/contribuTP' val,unnest(string_to_array(change->>'change/village',' '))village from t) select _union,bp,village,val,(select village_type from village_typedef where village=q.village) village_type,count(*) frq from q group by village,val,_union,bp ) select bp,( CASE bp WHEN '1' THEN 'Fun center Girls-BP1' WHEN '2' THEN 'Fun center Boys-BP2' WHEN '3' THEN 'Mothers(FC adolescent) -BP3' WHEN '4' THEN 'Fathers(FC Adolescent) -BP4' WHEN '5' THEN 'EVAW Forum -BP5' WHEN '6' THEN 'Role Model -BP6' WHEN '7' THEN 'CV-BP7' WHEN '8' THEN 'CF-BP8' WHEN '9' THEN 'Others-FF-BP9' END )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    contrib_chart_data = json.dumps(__db_fetch_values_dict(contrib_chart_query), default=decimal_default)

    filter_json = get_report_filters_value(request, 'bd')

    variables = RequestContext(request, {
        'rpt_type': 'bd',
        'change_data': change_data,
        'filter_json': filter_json,
        'unexpected_chart_data': unexpected_chart_data,
        'positive_chart_data': positive_chart_data,
        'majorminor_chart_data': majorminor_chart_data,
        'contrib_chart_data': contrib_chart_data
    })
    return render(request, 'bd_obsrv_jrnal_toc.html', variables)


def np_obsrv_jrnal_toc(request):
    change_query = "with q as(with t as(SELECT json->>'basic/pngo' tmp_pngo, json->>'basic/vdc' vdc,json_array_elements((json->>'change')::json) change from public.vwapprovedlogger_instance where xform_id=305 and(json->>'basic/month')::Date between '1-1-2016' and '1-1-2017' ) select 'contribuTP' change_type,change->>'change/contriTP' val,(case change->>'change/contriTP' when '1' then '0_20' when '2' then '20_40' when '3' then '40_60' when '4' then '60_80' when '5' then '80_100' end) txt from t union all select 'MajorMinor' change_type,change->>'change/changeMajorMinor' val,(case change->>'change/changeMajorMinor' when '1' then 'Major' when '2' then 'Important' when '3' then 'Minor' end) txt from t union all select 'PositiveNegative' change_type,change->>'change/changePositiveNegative' val, (case change->>'change/changePositiveNegative' when '1' then 'Positive' when '2' then 'Negative' end) txt from t union all select 'ExpectUnexpect' change_type,change->>'change/changeExpectUnexpect' val, (case change->>'change/changeExpectUnexpect' when '1' then 'Expected' when '2' then 'Unexpected' end) txt from t) select change_type,val,txt,count(*) frq from q group by change_type,val,txt order by 1,2"
    change_data = json.dumps(__db_fetch_values_dict(change_query))

    unexpected_chart_query = "with p as( with q as(with t as(select vdc,json_array_elements(change) change from vwnpobservationjournal) select vdc as village,change->>'change/boundaryPart' bp,change->>'change/changeExpectUnexpect' val from t) select bp,village,val,count(*) frq from q group by village,val,bp ) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    unexpected_chart_data = json.dumps(__db_fetch_values_dict(unexpected_chart_query), default=decimal_default)

    positive_chart_query = "with p as(with q as(with t as(select vdc,json_array_elements(change) change from vwnpobservationjournal) select change->>'change/boundaryPart' bp,change->>'change/changePositiveNegative' val,vdc as village from t) select bp,village,val,count(*) frq from q group by village,val,bp ) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    positive_chart_data = json.dumps(__db_fetch_values_dict(positive_chart_query), default=decimal_default)

    majorminor_chart_query = "with p as(with q as(with t as(select vdc,json_array_elements(change) change from vwnpobservationjournal) select change->>'change/boundaryPart' bp,change->>'change/changeMajorMinor' val,vdc as village from t) select bp,village,val,count(*) frq from q group by village,val,bp ) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    majorminor_chart_data = json.dumps(__db_fetch_values_dict(majorminor_chart_query), default=decimal_default)

    contrib_chart_query = "with p as( with q as( with t as(select vdc,json_array_elements(change) change from vwnpobservationjournal) select change->>'change/boundaryPart' bp,change->>'change/contriTP' val,vdc as village from t) select bp,village,val,count(*) frq from q group by village,val,bp ) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end ) bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    contrib_chart_data = json.dumps(__db_fetch_values_dict(contrib_chart_query), default=decimal_default)

    filter_json = get_report_filters_value(request, 'np')

    variables = RequestContext(request, {
        'rpt_type': 'np',
        'change_data': change_data,
        'filter_json': filter_json,
        'unexpected_chart_data': unexpected_chart_data,
        'positive_chart_data': positive_chart_data,
        'majorminor_chart_data': majorminor_chart_data,
        'contrib_chart_data': contrib_chart_data
    })
    return render(request, 'np_obsrv_jrnal_toc.html', variables)


def observation_journal_fd(request):
    progress_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal) select change->>'change/union' _union,change->>'change/boundaryPart' bp,unnest(string_to_array(change->>'change/village',' '))village, change->>'change/progressMarker' prm from t) select _union,bp,(select pm_type from progressmaker_mapping where progress_maker=q.prm)prm_type,village,(select village_type from village_typedef where village=q.village) village_type,count(*) frq from q group by village,_union,bp,prm ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers (FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text, prm_type,sum(frq) from p group by bp,prm_type order by 2,3"
    progress_data = json.dumps(__db_fetch_values_dict(progress_query), default=decimal_default)

    outcome_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal) select change->>'change/union' _union,change->>'change/boundaryPart' bp,unnest(string_to_array(change->>'change/village',' '))village, change->>'change/outcomeNum' outcome from t) select _union,bp,village,(select village_type from village_typedef where village=q.village) village_type, unnest(string_to_array(outcome,' ')) outcome from q order by 1,2 ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers (FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text, outcome,count(*) from p group by bp,outcome order by 2,3"
    outcome_data = json.dumps(__db_fetch_values_dict(outcome_query), default=decimal_default)

    filter_json = get_report_filters_value(request, 'bd')

    variables = RequestContext(request, {
        'rpt_type': 'bd',
        'progress_data': progress_data,
        'filter_json': filter_json,
        'outcome_data': outcome_data
    })
    return render(request, 'bd_obsrv_jrnal_fd.html', variables)


def np_observation_journal_fd(request):
    progress_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal) select change->>'change/union' _union,change->>'change/boundaryPart' bp,unnest(string_to_array(change->>'change/village',' '))village, change->>'change/progressMarker' prm from t) select _union,bp,(select pm_type from progressmaker_mapping where progress_maker=q.prm)prm_type,village,(select village_type from village_typedef where village=q.village) village_type,count(*) frq from q group by village,_union,bp,prm ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers (FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text, prm_type,sum(frq) from p group by bp,prm_type order by 2,3"
    progress_data = json.dumps(__db_fetch_values_dict(progress_query), default=decimal_default)

    outcome_query = "with p as( with q as(with t as(select vdc, json_array_elements(change) change from vwnpobservationjournal) select change->>'change/boundaryPart' bp, vdc as village, change->>'change/outcomeNum' outcome from t) select bp,village,unnest(string_to_array(outcome,' ')) outcome from q order by 1,2 ) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end )bp_text, outcome,count(*) from p group by bp,outcome order by 2,3"
    outcome_data = json.dumps(__db_fetch_values_dict(outcome_query), default=decimal_default)

    filter_json = get_report_filters_value(request, 'np')

    variables = RequestContext(request, {
        'rpt_type': 'np',
        'progress_data': progress_data,
        'filter_json': filter_json,
        'outcome_data': outcome_data
    })
    return render(request, 'np_obsrv_jrnal_fd.html', variables)


def np_observation_journal_filter(request):
    pngo_name = request.POST.get('pngo')
    ff_scm = request.POST.get('ff_scm')
    vdc_name = request.POST.get('vdc_name')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    if pngo_name == '':
        pngo_name = '%'
    if vdc_name == '':
        vdc_name = '%'
    if ff_scm == '':
        ff_scm = '%'
    if start_date == '':
        start_date = '01-01-2016'
    if end_date == '':
        end_date = datetime.datetime.now().strftime("%m-%d-%Y")

    change_query = "with q as(with t as(SELECT json->>'basic/smName' tmp_sm, json->>'basic/pngo' tmp_pngo, json->>'basic/vdc' vdc,json_array_elements((json->>'change')::json) change from public.vwapprovedlogger_instance where xform_id=305 and(json->>'basic/month')::Date between '" + str(
        start_date) + "' and '" + str(end_date) + "' and json->>'basic/smName' LIKE '" + str(
        ff_scm) + "' and json->>'basic/pngo' LIKE '" + str(pngo_name) + "' and json->>'basic/vdc' LIKE '" + str(
        vdc_name) + "') select 'contribuTP' change_type,change->>'change/contriTP' val,(case change->>'change/contriTP' when '1' then '0_20' when '2' then '20_40' when '3' then '40_60' when '4' then '60_80' when '5' then '80_100' end) txt from t union all select 'MajorMinor' change_type,change->>'change/changeMajorMinor' val,(case change->>'change/changeMajorMinor' when '1' then 'Major' when '2' then 'Important' when '3' then 'Minor' end) txt from t union all select 'PositiveNegative' change_type,change->>'change/changePositiveNegative' val, (case change->>'change/changePositiveNegative' when '1' then 'Positive' when '2' then 'Negative' end) txt from t union all select 'ExpectUnexpect' change_type,change->>'change/changeExpectUnexpect' val, (case change->>'change/changeExpectUnexpect' when '1' then 'Expected' when '2' then 'Unexpected' end) txt from t) select change_type,val,txt,count(*) frq from q group by change_type,val,txt order by 1,2"
    change_data = json.dumps(__db_fetch_values_dict(change_query))

    unexpected_chart_query = "with p as( with q as (with t as (select vdc,json_array_elements(change) change from vwnpobservationjournal where vdc LIKE '" + vdc_name + "' and tmp_pngo LIKE '" + str(
        pngo_name) + "' and ffname LIKE '" + str(ff_scm) + "' and _date between '" + str(start_date) + "' and '" + str(
        end_date) + "') select vdc as village,change->>'change/boundaryPart' bp,change->>'change/changeExpectUnexpect' val from t) select bp,village,val,count(*) frq from q group by village,val,bp) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    unexpected_chart_data = json.dumps(__db_fetch_values_dict(unexpected_chart_query), default=decimal_default)

    positive_chart_query = "with p as(with q as(with t as(select vdc,json_array_elements(change) change from vwnpobservationjournal where vdc LIKE '" + vdc_name + "' and tmp_pngo LIKE '" + str(
        pngo_name) + "' and ffname LIKE '" + str(ff_scm) + "' and _date between '" + str(start_date) + "' and '" + str(
        end_date) + "') select change->>'change/boundaryPart' bp,change->>'change/changePositiveNegative' val,vdc as village from t) select bp,village,val,count(*) frq from q group by village,val,bp ) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    positive_chart_data = json.dumps(__db_fetch_values_dict(positive_chart_query), default=decimal_default)

    majorminor_chart_query = "with p as(with q as(with t as(select vdc,json_array_elements(change) change from vwnpobservationjournal where vdc LIKE '" + vdc_name + "' and tmp_pngo LIKE '" + str(
        pngo_name) + "' and ffname LIKE '" + str(ff_scm) + "' and _date between '" + str(start_date) + "' and '" + str(
        end_date) + "') select change->>'change/boundaryPart' bp,change->>'change/changeMajorMinor' val,vdc as village from t) select bp,village,val,count(*) frq from q group by village,val,bp) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end )bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    majorminor_chart_data = json.dumps(__db_fetch_values_dict(majorminor_chart_query), default=decimal_default)

    contrib_chart_query = "with p as( with q as( with t as(select vdc,json_array_elements(change) change from vwnpobservationjournal where vdc LIKE '" + vdc_name + "' and tmp_pngo LIKE '" + str(
        pngo_name) + "' and ffname LIKE '" + str(ff_scm) + "' and _date between '" + str(start_date) + "' and '" + str(
        end_date) + "') select change->>'change/boundaryPart' bp,change->>'change/contriTP' val,vdc as village from t) select bp,village,val,count(*) frq from q group by village,val,bp ) select bp,(case bp when '1' then 'Girls group' when '2' then 'Boys group' when '3' then 'Parents group' when '4' then 'VCPC' when '5' then 'Religious Leaders' when '6' then 'Child Club' when '7' then'School Management Committee' when '8' then'Group Facilitator' when '9' then 'Other' end ) bp_text,val,sum(frq) from p group by bp,val order by bp,val"
    contrib_chart_data = json.dumps(__db_fetch_values_dict(contrib_chart_query), default=decimal_default)

    return HttpResponse(json.dumps({'change_data': change_data,
                                    'unexpected_chart_data': unexpected_chart_data,
                                    'positive_chart_data': positive_chart_data,
                                    'majorminor_chart_data': majorminor_chart_data,
                                    'contrib_chart_data': contrib_chart_data}))


def observation_journal_filter(request):
    pngo_name = request.POST.get('pngo')
    upozilla_name = request.POST.get('upozilla_name')
    union_name = request.POST.get('union_name')
    village_name = request.POST.get('village_name')
    village_type = request.POST.get('village_type')
    ff_scm = request.POST.get('ff_scm')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')

    if start_date == '':
        start_date = '01-01-2016'
    if end_date == '':
        end_date = datetime.datetime.now().strftime("%m-%d-%Y")

    fdcs_change_replacement = ""
    change_change_replacement = ""
    progress_json_replacement = " where _date::Date between '" + str(start_date) + "' and '" + str(end_date) + "'"
    fdcs_json_replacement = " and (json->>'geo/month')::Date between '" + str(start_date) + "' and '" + str(
        end_date) + "'"
    fdcs_vill_type_replacement = ""

    if pngo_name != '' and pngo_name is not None:
        fdcs_json_replacement += " and json->>'geo/pngo' = '" + str(pngo_name) + "' "
        progress_json_replacement += " and tmp_pngo = '" + str(pngo_name) + "' "
    if upozilla_name != '' and upozilla_name is not None:
        fdcs_json_replacement += " and json->>'geo/upazila' = '" + str(upozilla_name) + "' "
        progress_json_replacement += " and upazilla = '" + str(upozilla_name) + "' "
    if ff_scm != '' and ff_scm is not None:
        fdcs_json_replacement += " and json->>'geo/ffName' = '" + str(ff_scm) + "'"
        progress_json_replacement += " and ffname = '" + str(ff_scm) + "'"

    if union_name != '' and  union_name is not None:
        if fdcs_change_replacement == '':
            fdcs_change_replacement += " where change->>'change/union' = '" + str(union_name) + "' "
        else:
            fdcs_change_replacement += " and change->>'change/union' = '" + str(union_name) + "' "

        if change_change_replacement == '':
            change_change_replacement += " where change->>'change/union' = '" + str(union_name) + "' "
        else:
            change_change_replacement += " and change->>'change/union' = '" + str(union_name) + "' "

    if village_name != '' and village_name is not None:
        if fdcs_change_replacement == '':
            fdcs_change_replacement += " where change->>'change/village' = '" + str(village_name) + "' "
        else:
            fdcs_change_replacement += " and change->>'change/village' = '" + str(village_name) + "' "

        if change_change_replacement == '':
            change_change_replacement += " where change->>'change/union' = '" + str(union_name) + "' "
        else:
            change_change_replacement += " and change->>'change/union' = '" + str(union_name) + "' "

    if village_type != '' and village_type is not None:
        fdcs_vill_type_replacement = " where vill_type = '" + str(village_type) + "' "
        if change_change_replacement == '':
            change_change_replacement += " where vill_type = '" + str(village_type) + "' "
        else:
            change_change_replacement += " and vill_type = '" + str(village_type) + "' "

    fdcs_query = "with q as( with t as( SELECT json->>'geo/pngo' tmp_pngo, json_array_elements((json->>'change')::json) change FROM public.vwapprovedlogger_instance where xform_id=252 " + str(
        fdcs_json_replacement) + ") select change->>'change/boundaryPart' boundar_part, (SELECT village_type FROM public.village_typedef where village = change->>'change/village') vill_type from t " + str(
        fdcs_change_replacement) + ") select (case boundar_part when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers (FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end),count(*) from q " + str(
        fdcs_vill_type_replacement) + " group by boundar_part"
    fdcs_data = json.dumps(__db_fetch_values_dict(fdcs_query))

    change_query = "WITH q AS( WITH t AS( SELECT json->>'geo/pngo' tmp_pngo, Json_array_elements((json->>'change')::json) change FROM public.vwapprovedlogger_instance WHERE xform_id=252 " + str(
        fdcs_json_replacement) + ") SELECT 'contribuTP' change_type, change, change->>'change/contribuTP' val, (SELECT village_type FROM public.village_typedef where village = change->>'change/village') vill_type,( CASE change->>'change/contribuTP' WHEN '1' THEN '0_20' WHEN '2' THEN '40_60' WHEN '3' THEN '80_100' END) txt FROM t UNION ALL SELECT 'MajorMinor' change_type, change, change->>'change/MajorMinor' val, (SELECT village_type FROM public.village_typedef where village = change->>'change/village') vill_type,( CASE change->>'change/MajorMinor' WHEN '1' THEN 'Major' WHEN '2' THEN 'Minor' WHEN '3' THEN 'Important' END) txt FROM t UNION ALL SELECT 'PositiveNegative' change_type,change, change->>'change/PositiveNegative' val, (SELECT village_type FROM public.village_typedef where village = change->>'change/village') vill_type,( CASE change->>'change/PositiveNegative' WHEN '1' THEN 'Positive' WHEN '2' THEN 'Negative' END) txt FROM t UNION ALL SELECT 'ExpectUnexpect' change_type,change , change->>'change/ExpectUnexpect' val, (SELECT village_type FROM public.village_typedef where village = change->>'change/village') vill_type,( CASE change->>'change/ExpectUnexpect' WHEN '1' THEN 'Expected' WHEN '2' THEN 'Unexpected' END) txt FROM t) SELECT change_type, val, txt, count(*) frq FROM q " + str(
        change_change_replacement) + " GROUP BY change_type, val, txt ORDER BY 1, 2"
    change_data = json.dumps(__db_fetch_values_dict(change_query))

    progress_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal " + str(
        progress_json_replacement) + ") select change->>'change/union' _union,change->>'change/boundaryPart' bp,unnest(string_to_array(change->>'change/village',' '))village,(SELECT village_type FROM public.village_typedef where village = change->>'change/village') vill_type, change->>'change/progressMarker' prm from t " + str(
        fdcs_change_replacement) + ") select _union,bp,(select pm_type from progressmaker_mapping where progress_maker=q.prm)prm_type,village,(select village_type from village_typedef where village=q.village) village_type,count(*) frq from q " + str(
        fdcs_vill_type_replacement) + " group by village,_union,bp,prm ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers (FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text, prm_type,sum(frq) from p group by bp,prm_type order by 2,3"
    progress_data = json.dumps(__db_fetch_values_dict(progress_query), default=decimal_default)

    outcome_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal " + str(
        progress_json_replacement) + ") select change->>'change/union' _union,change->>'change/boundaryPart' bp,unnest(string_to_array(change->>'change/village',' '))village, change->>'change/outcomeNum' outcome from t " + str(
        fdcs_change_replacement) + ") select _union,bp,village,(select village_type from village_typedef where village=q.village) vill_type, unnest(string_to_array(outcome,' ')) outcome from q order by 1,2 ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers (FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text, outcome,count(*) from p " + str(
        fdcs_vill_type_replacement) + " group by bp,outcome order by 2,3"
    outcome_data = json.dumps(__db_fetch_values_dict(outcome_query), default=decimal_default)

    unexpected_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal " + progress_json_replacement + ") select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/ExpectUnexpect' val,unnest(string_to_array(change->>'change/village',' '))village from t " + fdcs_change_replacement + ") select _union,bp,village,val,(select village_type from village_typedef where village=q.village) vill_type,count(*) frq from q group by village,val,_union,bp ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers(FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text,val,sum(frq) from p " + fdcs_vill_type_replacement + " group by bp,val order by bp,val"
    unexpected_chart_data = json.dumps(__db_fetch_values_dict(unexpected_chart_query), default=decimal_default)

    positive_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal " + progress_json_replacement + ") select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/PositiveNegative' val,unnest(string_to_array(change->>'change/village',' '))village from t " + fdcs_change_replacement + ") select _union,bp,village,val,(select village_type from village_typedef where village=q.village) vill_type,count(*) frq from q group by village,val,_union,bp ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers(FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text,val,sum(frq) from p " + fdcs_vill_type_replacement + " group by bp,val order by bp,val"
    positive_chart_data = json.dumps(__db_fetch_values_dict(positive_chart_query), default=decimal_default)

    majorminor_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal " + progress_json_replacement + ") select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/MajorMinor' val,unnest(string_to_array(change->>'change/village',' '))village from t " + fdcs_change_replacement + ") select _union,bp,village,val,(select village_type from village_typedef where village=q.village) vill_type,count(*) frq from q group by village,val,_union,bp ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers(FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text,val,sum(frq) from p " + fdcs_vill_type_replacement + " group by bp,val order by bp,val"
    majorminor_chart_data = json.dumps(__db_fetch_values_dict(majorminor_chart_query), default=decimal_default)

    contrib_chart_query = "with p as( with q as( with t as(select json_array_elements(change) change from vwbdobservationjournal " + progress_json_replacement + ") select change->>'change/union' _union,change->>'change/boundaryPart' bp,change->>'change/contribuTP' val,unnest(string_to_array(change->>'change/village',' '))village from t " + fdcs_change_replacement + ") select _union,bp,village,val,(select village_type from village_typedef where village=q.village) vill_type,count(*) frq from q group by village,val,_union,bp ) select bp,(case bp when '1' then 'Fun center Girls-BP1' when '2' then 'Fun center Boys-BP2' when '3' then 'Mothers(FC adolescent) -BP3' when '4' then 'Fathers (FC Adolescent) -BP4' when '5' then 'EVAW Forum -BP5' when '6' then 'Role Model -BP6' when '7' then 'CV-BP7' when '8' then 'CF-BP8' when '9' then 'Others-FF-BP9' end )bp_text,val,sum(frq) from p " + fdcs_vill_type_replacement + " group by bp,val order by bp,val"
    contrib_chart_data = json.dumps(__db_fetch_values_dict(contrib_chart_query), default=decimal_default)

    return HttpResponse(json.dumps({'fdcs_data': fdcs_data, 'change_data': change_data, 'progress_data': progress_data,
                                    'outcome_data': outcome_data, 'unexpected_chart_data': unexpected_chart_data,
                                    'positive_chart_data': positive_chart_data,
                                    'majorminor_chart_data': majorminor_chart_data,
                                    'contrib_chart_data': contrib_chart_data}))


def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]


def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj
