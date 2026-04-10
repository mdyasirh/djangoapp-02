import datetime

from django.db import models
from django.contrib.auth.models import User


class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employeeprofile")
    pin = models.CharField(max_length=4, help_text="4-digit PIN for quick login")
    target_hours_per_month = models.DecimalField(max_digits=6, decimal_places=2, default=160.0)
    department = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class DailyTimeRecord(models.Model):
    STATUS_CHOICES = [
        ("WORKING", "Working"),
        ("ON_BREAK", "On Break"),
        ("CLOCKED_OUT", "Clocked Out"),
        ("MISSING_CLOCKOUT", "Missing Clock-out"),
    ]

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="time_records")
    date = models.DateField(default=datetime.date.today)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    break_start = models.DateTimeField(null=True, blank=True)
    total_break_minutes = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="WORKING")

    class Meta:
        ordering = ["-date"]
        unique_together = ["employee", "date"]

    def __str__(self):
        return f"{self.employee} – {self.date} ({self.status})"

    @property
    def net_hours(self):
        """Return net working hours as a float, or None if incomplete."""
        if self.clock_in and self.clock_out:
            delta = (self.clock_out - self.clock_in).total_seconds() / 3600.0
            return round(delta - (self.total_break_minutes / 60.0), 2)
        return None


class CorrectionRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
    ]

    record = models.ForeignKey(DailyTimeRecord, on_delete=models.CASCADE, related_name="corrections")
    proposed_out_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    def __str__(self):
        return f"Correction for {self.record} – {self.status}"


class HRReview(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("REMINDER_SENT", "Reminder Sent"),
        ("REVIEWED", "Reviewed"),
    ]

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="hr_reviews")
    month = models.IntegerField(help_text="Month number (1-12)")
    year = models.IntegerField(default=2024)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    class Meta:
        unique_together = ["employee", "month", "year"]

    def __str__(self):
        return f"HRReview {self.employee} – {self.month}/{self.year} ({self.status})"
