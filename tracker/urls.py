from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.login_view),

    # Employee dashboard
    path("clock/", views.punch_clock_view, name="punch_clock"),

    # Employee AJAX endpoints
    path("api/punch-in/", views.api_punch_in, name="api_punch_in"),
    path("api/break-start/", views.api_break_start, name="api_break_start"),
    path("api/break-end/", views.api_break_end, name="api_break_end"),
    path("api/punch-out/", views.api_punch_out, name="api_punch_out"),
    path("api/submit-correction/", views.api_submit_correction, name="api_submit_correction"),
    path("api/delete-record/", views.api_delete_record, name="api_delete_record"),

    # Notification endpoints
    path("api/notifications/", views.api_notifications, name="api_notifications"),
    path("api/notifications/mark-read/", views.api_mark_notification_read, name="api_mark_notification_read"),
    path("api/notifications/mark-all-read/", views.api_mark_all_notifications_read, name="api_mark_all_notifications_read"),

    # HR dashboard
    path("hr/", views.hr_dashboard_view, name="hr_dashboard"),
    path("access-denied/", views.access_denied_view, name="access_denied"),

    # HR AJAX endpoints
    path("api/send-reminder/", views.api_send_reminder, name="api_send_reminder"),
    path("api/acknowledge/", views.api_acknowledge, name="api_acknowledge"),

    # CSV export
    path("hr/export-csv/", views.csv_export_view, name="csv_export"),
]
