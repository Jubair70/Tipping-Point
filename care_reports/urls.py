from django.conf.urls import patterns, include, url
from django.contrib import admin
from onadata.apps.care_reports import views

urlpatterns = patterns('',
    # url(r'^$', views.index, name='index'),
    url(r'^bd_attendence_activity/$', views.get_report_bd_attendence_activity, name='get_report_bd_attendence_activity'),
    url(r'^np_attendence_activity/$', views.get_report_np_attendence_activity, name='get_report_np_attendence_activity'),

    url(r'^bd_topic_activity/$', views.get_report_bd_attendence_topic, name='get_report_bd_attendence_topic'),
    url(r'^np_topic_activity/$', views.get_report_np_attendence_topic, name='get_report_np_attendence_topic'),

    url(r'^bd_other_activity/$', views.get_report_bd_others_activities, name='get_report_bd_others_activities'),
    url(r'^np_other_activity/$', views.get_report_np_others_activities, name='get_report_np_others_activities'),

    url(r'^bd_adolescents_status/$', views.get_report_bd_adolescents_status, name='get_report_bd_adolescents_status'),
    url(r'^np_adolescents_status/$', views.get_report_np_adolescents_status, name='get_report_np_adolescents_status'),

    url(r'^bd_g_b_status_change/$', views.get_report_bd_girl_boy_status_change, name='get_report_bd_girl_boy_status_change'),
    url(r'^np_g_b_status_change/$', views.get_report_np_girl_boy_status_change, name='get_report_np_girl_boy_status_change'),

    url(r'^bd_staff_trans/$', views.get_report_bd_staff_transformation, name='get_report_bd_staff_transformation'),
    url(r'^operational-status/$',views.get_report_operation_status,name='get_report_operation_status' ),
    url(r'^bd_outcome_jrnal_topic/$', views.get_report_bd_outcome_adolescent_journal, name='get_report_bd_outcome_adolescent_journal'),
    url(r'^np_outcome_jrnal_topic/$', views.get_report_np_outcome_adolescent_journal, name='get_report_np_outcome_adolescent_journal'),
    url(r'^bd_outcome_jrnal_attendance/$', views.get_report_bd_outcome_journal, name='get_report_bd_outcome_journal'),
    url(r'^bd_outcome_jrnal_others/$', views.get_report_bd_outcome_others_journal,
                           name='get_report_bd_outcome_others_journal'),

    url(r'^bd_obsrv_jrnal/$', views.observation_journal, name='bd_obsrv_jrnal'),
        url(r'^np_obsrv_jrnal/$', views.np_observation_journal, name='np_obsrv_jrnal'),

    url(r'^bd_obsrv_jrnal_toc/$', views.bd_obsrv_jrnal_toc, name='bd_obsrv_jrnal_toc'),
    url(r'^np_obsrv_jrnal_toc/$', views.np_obsrv_jrnal_toc, name='np_obsrv_jrnal_toc'),
    url(r'^observation_journal_fd/$', views.observation_journal_fd, name='observation_journal_fd'),
    url(r'^np_observation_journal_fd/$', views.np_observation_journal_fd, name='np_observation_journal_fd'),
    url(r'^bd_observation_journal_filter/$', views.observation_journal_filter, name='bd_observation_journal_filter'),
    url(r'^np_observation_journal_filter/$', views.np_observation_journal_filter, name='np_observation_journal_filter'),
    )
