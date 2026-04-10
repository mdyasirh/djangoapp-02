import csv
import datetime
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import CorrectionRequest, DailyTimeRecord, EmployeeProfile, HRReview


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_hr(user):
    return user.groups.filter(name="HR").exists()


def _today_record(profile):
    """Get or create today's DailyTimeRecord for the given profile."""
    today = datetime.date.today()
    record, _created = DailyTimeRecord.objects.get_or_create(
        employee=profile,
        date=today,
        defaults={"status": "WORKING"},
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
# Employee punch-clock page
# ---------------------------------------------------------------------------

@login_required
def punch_clock_view(request):
    profile = request.user.employeeprofile
    today = datetime.date.today()

    # Current record (if any)
    record = DailyTimeRecord.objects.filter(employee=profile, date=today).first()

    # Weekly overview: last 7 days (excluding today)
    week_start = today - datetime.timedelta(days=7)
    weekly_records = (
        DailyTimeRecord.objects.filter(employee=profile, date__gte=week_start, date__lt=today)
        .order_by("date")
    )

    ctx = {
        "profile": profile,
        "record": record,
        "weekly_records": weekly_records,
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

    record, created = DailyTimeRecord.objects.get_or_create(
        employee=profile,
        date=today,
        defaults={"clock_in": timezone.now(), "status": "WORKING"},
    )
    if not created and record.clock_in is None:
        record.clock_in = timezone.now()
        record.status = "WORKING"
        record.save()
    elif not created:
        return JsonResponse({"ok": False, "error": "Already clocked in today."})

    return JsonResponse({
        "ok": True,
        "status": record.status,
        "clock_in": record.clock_in.strftime("%H:%M"),
    })


@login_required
@require_POST
def api_break_start(request):
    profile = request.user.employeeprofile
    record = _today_record(profile)

    if record.status != "WORKING":
        return JsonResponse({"ok": False, "error": "Not currently working."})

    record.break_start = timezone.now()
    record.status = "ON_BREAK"
    record.save()
    return JsonResponse({"ok": True, "status": record.status})


@login_required
@require_POST
def api_break_end(request):
    profile = request.user.employeeprofile
    record = _today_record(profile)

    if record.status != "ON_BREAK":
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
    record = _today_record(profile)

    if record.status not in ("WORKING", "ON_BREAK"):
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
        "clock_out": record.clock_out.strftime("%H:%M"),
        "net_hours": record.net_hours,
        "break_min": record.total_break_minutes,
    })


@login_required
@require_POST
def api_submit_correction(request):
    profile = request.user.employeeprofile
    record_id = request.POST.get("record_id")
    proposed_time = request.POST.get("proposed_time")  # HH:MM

    try:
        record = DailyTimeRecord.objects.get(pk=record_id, employee=profile)
    except DailyTimeRecord.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Record not found."})

    hour, minute = proposed_time.split(":")
    t = datetime.time(int(hour), int(minute))

    CorrectionRequest.objects.create(record=record, proposed_out_time=t)
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# HR Dashboard
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_hr, login_url="/access-denied/")
def hr_dashboard_view(request):
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year

    employees = EmployeeProfile.objects.select_related("user").all()
    employee_data = []

    for emp in employees:
        records = DailyTimeRecord.objects.filter(
            employee=emp,
            date__month=current_month,
            date__year=current_year,
        ).order_by("date")

        actual_hours = Decimal("0.0")
        for r in records:
            if r.net_hours is not None:
                actual_hours += Decimal(str(r.net_hours))

        target = emp.target_hours_per_month
        delta = actual_hours - target

        # HR review status
        hr_review, _ = HRReview.objects.get_or_create(
            employee=emp,
            month=current_month,
            year=current_year,
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

    ctx = {
        "employee_data": employee_data,
        "current_month": current_month,
        "current_year": current_year,
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
    try:
        review = HRReview.objects.get(pk=review_id)
    except HRReview.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Review not found."})

    review.status = "REMINDER_SENT"
    review.save()
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
    current_month = today.month
    current_year = today.year

    records = (
        DailyTimeRecord.objects.filter(date__month=current_month, date__year=current_year)
        .select_related("employee__user")
        .order_by("employee__user__last_name", "date")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="time_report_{current_year}_{current_month:02d}.csv"'

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
