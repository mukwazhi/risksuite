from django.urls import path
from . import views

urlpatterns = [
    path('my-risks/<str:risk_id>/', views.risk_owner_detailed, name='risk_owner_detailed'),
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard and main views
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('home/', views.dashboard, name='home'),
    path('actions/', views.actions_dashboard, name='actions_dashboard'),
    path('matrix/', views.risk_matrix, name='risk_matrix'),
    path('debug/risks-by-dept/', views.debug_risks_by_dept, name='debug_risks_by_dept'),
    
    # Workflow pages
    path('workflow/parked/', views.parked_risks, name='parked_risks'),
    path('workflow/pending/', views.pending_risks, name='pending_risks'),
    path('workflow/approved/', views.approved_risks, name='approved_risks'),
    path('workflow/rejected/', views.rejected_risks, name='rejected_risks'),
    
    # Risk CRUD operations
    path('create/', views.create_risk, name='create_risk'),
    path('risks/', views.all_risks, name='all_risks'),
    path('risks/<str:risk_id>/', views.risk_view, name='risk_detail'),
    path('risks/<str:risk_id>/edit/', views.edit_risk, name='edit_risk'),
    path('risks/<str:risk_id>/download-report/', views.download_risk_report_pdf, name='download_risk_report'),
    
    # Risk workflow actions
    path('risks/<int:risk_id>/submit/', views.submit_risk, name='submit_risk'),
    path('risks/<int:risk_id>/approve/', views.approve_risk, name='approve_risk'),
    path('risks/<int:risk_id>/reject/', views.reject_risk, name='reject_risk'),
    path('risks/<int:risk_id>/delete/', views.soft_delete_risk, name='soft_delete_risk'),
    path('risks/<int:risk_id>/restore/', views.restore_risk, name='restore_risk'),
    
    # Risk assessments and mitigations
    path('risks/<str:risk_id>/add-assessment/', views.add_assessment, name='add_assessment'),
    path('risks/<str:risk_id>/assess-controls/', views.assess_controls, name='assess_controls'),
    path('risks/<str:risk_id>/add-mitigation/', views.add_mitigation, name='add_mitigation'),
    path('mitigations/<int:mitigation_id>/update/', views.update_mitigation, name='update_mitigation'),
    path('mitigations/<int:mitigation_id>/progress-trail/', views.mitigation_progress_trail, name='mitigation_progress_trail'),
    path('mitigations/history/', views.mitigations_history, name='mitigations_history'),
    path('risks/<str:risk_id>/add-indicator/', views.add_indicator, name='add_indicator'),
    
    # Indicator schedules and assessments
    path('schedules/<int:schedule_id>/update/', views.update_schedule, name='update_schedule'),
    path('schedules/<int:schedule_id>/record-assessment/', views.record_indicator_assessment, name='record_indicator_assessment'),
    path('indicators/<int:indicator_id>/assessments/', views.indicator_assessment_history, name='indicator_assessment_history'),
    path('indicators/<int:indicator_id>/generate-schedules/', views.generate_indicator_schedules, name='generate_indicator_schedules'),
    path('indicators/<int:indicator_id>/record-assessment/', views.record_indicator_assessment_for_indicator, name='record_indicator_assessment_for_indicator'),
    
    # Assessment decision workflow removed
    
    # Reports
    path('reports/', views.risk_report_options, name='risk_report_options'),
    path('reports/generate-pdf/', views.generate_risk_pdf_report, name='generate_risk_pdf'),
    path('reports/generate-detailed-pdf/', views.generate_detailed_risk_pdf_report, name='generate_detailed_risk_pdf'),
    
    # Audit trail
    # path('audit/', views.audit_trail, name='audit_trail'),  # Removed: view does not exist
    
    # Notification system removed — related views and templates deleted.
    # Notification preferences and test endpoint
    path('notifications/preferences/', views.notification_preferences, name='notification_preferences'),
    path('notifications/test/', views.notification_test_send, name='notification_test_send'),
    
    # Assessment Framework
    path('assessments/risk/<int:assessment_id>/', views.risk_assessment_detail, name='risk_assessment_detail'),
    path('assessments/dashboard/', views.assessment_dashboard, name='assessment_dashboard'),
    # Tasks overview
    path('tasks/', views.tasks, name='tasks'),
    
    # Risk Owner Dashboard
    path('my-dashboard/', views.risk_owner_dashboard, name='risk_owner_dashboard'),
    path('my-matrix/', views.risk_owner_matrix, name='risk_owner_matrix'),
    path('my-risks/<str:risk_id>/assessments/', views.risk_owner_assessment_history, name='risk_owner_assessment_history'),
    path('my-risks/<str:risk_id>/mitigations/history/', views.risk_owner_mitigation_history, name='risk_owner_mitigation_history'),
    path('global-dashboard/', views.global_dashboard, name='global_dashboard'),
    path('statistics/', views.global_dashboard, name='statistics'),
]
