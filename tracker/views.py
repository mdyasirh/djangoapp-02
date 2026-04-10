import csv
import datetime
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import CorrectionRequest, DailyTimeRecord, EmployeeProfile, HRReview, Notification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_hr(user):
    return user.groups.filter(name="HR").exists()


def _today_record(profile):
    """Get or create today's DailyTimeRecord for the given profile."""
    today = datetime.date.today()
    # Get the latest active (non-CLOCKED_OUT) record for today, or create new
    record = DailyTimeRecord.objects.filter(
        employee=profile,
        date=today,
        status__in=["WORKING", "ON_BREAK"],
    ).first()
    if record:
        return record
    # Create a new record for this shift
    record = DailyTimeRecord.objects.create(
        employee=profile,
        date=today,
        clock_in=timezone.now(),
        status="WORKING",
    )
    return record


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def login_view(request):
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if is_hr(user):
                return redirect("hr_dashboard")
            return redirect("punch_clock")
        error = "Invalid credentials."
    return render(request, "login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------------------------------------------------------------------
# Notification API endpoints
# ---------------------------------------------------------------------------

@login_required
def api_notifications(request):
    """Return unread notifications for the current user."""
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).values("id", "notification_type", "title", "message", "created_at", "is_read")
    return JsonResponse({
        "ok": True,
        "count": notifications.count(),
        "notifications": list(notifications),
    })


@login_required
@require_POST
def api_mark_notification_read(request):
    """Mark a notification as read."""
    notif_id = request.POST.get("notification_id")
    try:
        notif = Notification.objects.get(pk=notif_id, recipient=request.user)
    except Notification.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Notification not found."})

    notif.is_read = True
    notif.save()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def api_mark_all_notifications_read(request):
    """Mark all notifications as read for the current user."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Employee punch-clock page
# ---------------------------------------------------------------------------

@login_required
def punch_clock_view(request):
    profile = request.user.employeeprofile
    today = datetime.date.today()

    # Current active record (if any)
    record = DailyTimeRecord.objects.filter(
        employee=profile,
        date=today,
        status__in=["WORKING", "ON_BREAK"],
    ).first()

    # All completed records for today
    today_records = DailyTimeRecord.objects.filter(
        employee=profile,
        date=today,
        status="CLOCKED_OUT",
    ).order_by("clock_in")

    # Weekly overview: last 7 days (including today's completed records)
    week_start = today - datetime.timedelta(days=7)
    weekly_records = (
        DailyTimeRecord.objects.filter(employee=profile, date__gte=week_start, date__lte=today)
        .order_by("date", "clock_in")
    )

    # Notification count
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    ctx = {
        "profile": profile,
        "record": record,
        "today_records": today_records,
        "weekly_records": weekly_records,
        "unread_count": unread_count,
    }
    return render(request, "punch_clock.html", ctx)


# ---------------------------------------------------------------------------
# Employee AJAX endpoints
# ---------------------------------------------------------------------------

@login_required
@require_POST
def api_punch_in(request):
    profile = request.user.employeeprofile
    today = datetime.date.today()

    # Check for any active (non-clocked-out) record today
    active = DailyTimeRecord.objects.filter(
        employee=profile,
        date=today,
        status__in=["WORKING", "ON_BREAK"],
    ).first()

    if active:
        return JsonResponse({"ok": False, "error": "Already clocked in. Please clock out first."})

    record = DailyTimeRecord.objects.create(
        employee=profile,
        date=today,
        clock_in=timezone.now(),
        status="WORKING",
    )

    return JsonResponse({
        "ok": True,
        "status": record.status,
        "clock_in": record.clock_in.strftime("%H:%M"),
    })


@login_required
@require_POST
def api_break_start(request):
    profile = request.user.employeeprofile
    today = datetime.date.today()

    record = DailyTimeRecord.objects.filter(
        employee=profile, date=today, status="WORKING"
    ).first()

    if not record:
        return JsonResponse({"ok": False, "error": "Not currently working."})

    record.break_start = timezone.now()
    record.status = "ON_BREAK"
    record.save()
    return JsonResponse({"ok": True, "status": record.status})


@login_required
@require_POST
def api_break_end(request):
    profile = request.user.employeeprofile
    today = datetime.date.today()

    record = DailyTimeRecord.objects.filter(
        employee=profile, date=today, status="ON_BREAK"
    ).first()

    if not record:
        return JsonResponse({"ok": False, "error": "Not currently on break."})

    if record.break_start:
        delta = (timezone.now() - record.break_start).total_seconds()
        record.total_break_minutes += int(delta // 60)
    record.break_start = None
    record.status = "WORKING"
    record.save()
    return JsonResponse({"ok": True, "status": record.status, "break_min": record.total_break_minutes})


@login_required
@require_POST
def api_punch_out(request):
    profile = request.user.employeeprofile
    today = datetime.date.today()

    record = DailyTimeRecord.objects.filter(
        employee=profile, date=today, status__in=["WORKING", "ON_BREAK"]
    ).first()

    if not record:
        return JsonResponse({"ok": False, "error": "Cannot clock out."})

    # End any running break
    if record.status == "ON_BREAK" and record.break_start:
        delta = (timezone.now() - record.break_start).total_seconds()
        record.total_break_minutes += int(delta // 60)
        record.break_start = None

    record.clock_out = timezone.now()
    record.status = "CLOCKED_OUT"
    record.save()

    return JsonResponse({
        "ok": True,
        "status": record.status,
        "clock_in": record.clock_in.strftime("%H:%M") if record.clock_in else "",
        "clock_out": record.clock_out.strftime("%H:%M"),
        "net_hours": record.net_hours,
        "break_min": record.total_break_minutes,
    })


@login_required
@require_POST
def api_submit_correction(request):
    """Submit a correction/edit request for a time record."""
    profile = request.user.employeeprofile
    record_id = request.POST.get("record_id")
    proposed_clock_in = request.POST.get("proposed_clock_in", "").strip()
    proposed_clock_out = request.POST.get("proposed_clock_out", "").strip()
    proposed_break = request.POST.get("proposed_break_minutes", "").strip()
    note = request.POST.get("note", "").strip()

    try:
        record = DailyTimeRecord.objects.get(pk=record_id, employee=profile)
    except DailyTimeRecord.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Record not found."})

    correction_data = {"note": note}

    if proposed_clock_in:
        try:
            hour, minute = proposed_clock_in.split(":")
            correction_data["proposed_clock_in"] = datetime.time(int(hour), int(minute))
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "Invalid clock-in time format."})

    if proposed_clock_out:
        try:
            hour, minute = proposed_clock_out.split(":")
            correction_data["proposed_clock_out"] = datetime.time(int(hour), int(minute))
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "Invalid clock-out time format."})

    if proposed_break:
        try:
            correction_data["proposed_break_minutes"] = int(proposed_break)
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "Invalid break minutes."})

    correction = CorrectionRequest.objects.create(record=record, **correction_data)

    # Send notification to all HR users
    from django.contrib.auth.models import User
    hr_users = User.objects.filter(groups__name="HR")
    for hr_user in hr_users:
        Notification.objects.create(
            recipient=hr_user,
            sender=request.user,
            notification_type="EDIT_REQUEST",
            title=f"Bearbeitungsanfrage von {profile}",
            message=f"{profile} hat eine Korrektur für {record.date} angefragt. {note}",
            related_record=record,
        )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def api_delete_record(request):
    """Delete a time record (only own records, only CLOCKED_OUT)."""
    profile = request.user.employeeprofile
    record_id = request.POST.get("record_id")

    try:
        record = DailyTimeRecord.objects.get(pk=record_id, employee=profile)
    except DailyTimeRecord.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Record not found."})

    if record.status not in ("CLOCKED_OUT", "MISSING_CLOCKOUT"):
        return JsonResponse({"ok": False, "error": "Cannot delete an active record."})

    record.delete()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# HR Dashboard
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
def hr_dashboard_view(request):
    today = datetime.date.today()

    # Allow month/year selection, default to current month
    try:
        selected_month = int(request.GET.get("month", today.month))
        selected_year = int(request.GET.get("year", today.year))
    except (ValueError, TypeError):
        selected_month = today.month
        selected_year = today.year

    # Filter out HR group members from the employee list
    employees = EmployeeProfile.objects.select_related("user").exclude(
        user__groups__name="HR"
    ).all()

    employee_data = []

    for emp in employees:
        records = DailyTimeRecord.objects.filter(
            employee=emp,
            date__month=selected_month,
            date__year=selected_year,
        ).order_by("date", "clock_in")

        actual_hours = Decimal("0.0")
        for r in records:
            if r.net_hours is not None:
                actual_hours += Decimal(str(r.net_hours))

        target = emp.target_hours_per_month
        delta = actual_hours - target

        # HR review status
        hr_review, _ = HRReview.objects.get_or_create(
            employee=emp,
            month=selected_month,
            year=selected_year,
            defaults={"status": "PENDING"},
        )

        employee_data.append({
            "profile": emp,
            "target": target,
            "actual": round(actual_hours, 2),
            "delta": round(delta, 2),
            "records": records,
            "hr_review": hr_review,
        })

    # Notification count for HR
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    ctx = {
        "employee_data": employee_data,
        "current_month": selected_month,
        "current_year": selected_year,
        "unread_count": unread_count,
    }
    return render(request, "hr_dashboard.html", ctx)


def access_denied_view(request):
    return render(request, "access_denied.html", status=403)


# ---------------------------------------------------------------------------
# HR Action endpoints
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
@require_POST
def api_send_reminder(request):
    review_id = request.POST.get("review_id")
    message = request.POST.get("message", "").strip()
    try:
        review = HRReview.objects.get(pk=review_id)
    except HRReview.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Review not found."})

    review.status = "REMINDER_SENT"
    review.save()

    # Create actual notification for the employee
    default_msg = (
        f"Bitte überprüfen und korrigieren Sie Ihre Zeiteinträge für "
        f"{review.month}/{review.year}."
    )
    Notification.objects.create(
        recipient=review.employee.user,
        sender=request.user,
        notification_type="REMINDER",
        title=f"Erinnerung von HR",
        message=message if message else default_msg,
    )

    return JsonResponse({"ok": True, "status": review.status})


@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
@require_POST
def api_acknowledge(request):
    review_id = request.POST.get("review_id")
    try:
        review = HRReview.objects.get(pk=review_id)
    except HRReview.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Review not found."})

    review.status = "REVIEWED"
    review.save()
    return JsonResponse({"ok": True, "status": review.status})


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
def csv_export_view(request):
    today = datetime.date.today()

    try:
        selected_month = int(request.GET.get("month", today.month))
        selected_year = int(request.GET.get("year", today.year))
    except (ValueError, TypeError):
        selected_month = today.month
        selected_year = today.year

    records = (
        DailyTimeRecord.objects.filter(date__month=selected_month, date__year=selected_year)
        .select_related("employee__user")
        .exclude(employee__user__groups__name="HR")
        .order_by("employee__user__last_name", "date", "clock_in")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="time_report_{selected_year}_{selected_month:02d}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["Employee", "Date", "Clock-in", "Clock-out", "Break(min)", "Net Hours"])

    for r in records:
        writer.writerow([
            str(r.employee),
            r.date.isoformat(),
            r.clock_in.strftime("%H:%M") if r.clock_in else "",
            r.clock_out.strftime("%H:%M") if r.clock_out else "",
            r.total_break_minutes,
            r.net_hours if r.net_hours is not None else "",
        ])

    return response
