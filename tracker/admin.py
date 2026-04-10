from django.contrib import admin
from .models import CorrectionRequest, DailyTimeRecord, EmployeeProfile, HRReview


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "pin", "department", "target_hours_per_month")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(DailyTimeRecord)
class DailyTimeRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "clock_in", "clock_out", "total_break_minutes", "status")
    list_filter = ("status", "date")
    search_fields = ("employee__user__username",)


@admin.register(CorrectionRequest)
class CorrectionRequestAdmin(admin.ModelAdmin):
    list_display = ("record", "proposed_out_time", "status")
    list_filter = ("status",)


@admin.register(HRReview)
class HRReviewAdmin(admin.ModelAdmin):
    list_display = ("employee", "month", "year", "status")
    list_filter = ("status", "month", "year")
