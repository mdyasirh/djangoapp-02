"""
Management command to seed the database with demo data.
Creates groups, users, employee profiles, and historical time records.
"""
import datetime
import random

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import DailyTimeRecord, EmployeeProfile


class Command(BaseCommand):
    help = "Seed the database with demo employees and time records."

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        # Create HR group
        hr_group, _ = Group.objects.get_or_create(name="HR")

        # ---- Users & Profiles ----
        employees_data = [
            {"username": "lisa", "first": "Lisa", "last": "Müller", "pin": "1234", "dept": "Training", "target": 160},
            {"username": "tom", "first": "Tom", "last": "Fischer", "pin": "2345", "dept": "Training", "target": 160},
            {"username": "klara", "first": "Klara", "last": "Neumann", "pin": "3456", "dept": "Reception", "target": 140},
            {"username": "max", "first": "Max", "last": "Weber", "pin": "4567", "dept": "Maintenance", "target": 160},
            {"username": "anna", "first": "Anna", "last": "Schmidt", "pin": "5678", "dept": "Training", "target": 160},
        ]

        profiles = {}
        for emp in employees_data:
            user, created = User.objects.get_or_create(
                username=emp["username"],
                defaults={
                    "first_name": emp["first"],
                    "last_name": emp["last"],
                    "email": f"{emp['username']}@fitlife.de",
                },
            )
            if created:
                user.set_password(emp["pin"])
                user.save()
            profile, _ = EmployeeProfile.objects.get_or_create(
                user=user,
                defaults={
                    "pin": emp["pin"],
                    "department": emp["dept"],
                    "target_hours_per_month": emp["target"],
                },
            )
            profiles[emp["username"]] = profile
            self.stdout.write(f"  ✓ Employee: {user.get_full_name()} ({emp['username']})")

        # HR user
        hr_user, created = User.objects.get_or_create(
            username="hr",
            defaults={
                "first_name": "HR",
                "last_name": "Admin",
                "email": "hr@fitlife.de",
                "is_staff": True,
            },
        )
        if created:
            hr_user.set_password("hr1234")
            hr_user.save()
        hr_user.groups.add(hr_group)
        EmployeeProfile.objects.get_or_create(
            user=hr_user,
            defaults={"pin": "0000", "department": "Human Resources", "target_hours_per_month": 160},
        )
        self.stdout.write(f"  ✓ HR User: {hr_user.get_full_name()} (hr / hr1234)")

        # ---- Generate Historical Time Records (20 days) ----
        today = datetime.date.today()
        self.stdout.write("\nGenerating 20 days of historical records...")

        for username, profile in profiles.items():
            for day_offset in range(1, 21):
                record_date = today - datetime.timedelta(days=day_offset)

                # Skip weekends
                if record_date.weekday() >= 5:
                    continue

                # Tom Fischer: skip ~6 days to create > 5h deficit
                if username == "tom" and day_offset in (2, 4, 6, 8, 10, 12):
                    continue

                # Klara Neumann: work extra-long hours for > 5h overtime
                if username == "klara":
                    work_hours = random.uniform(9.0, 11.0)
                else:
                    work_hours = random.uniform(7.0, 8.5)

                break_minutes = random.randint(30, 60)

                clock_in_hour = random.randint(7, 9)
                clock_in_minute = random.randint(0, 59)
                clock_in_dt = timezone.make_aware(
                    datetime.datetime(record_date.year, record_date.month, record_date.day,
                                      clock_in_hour, clock_in_minute)
                )

                total_minutes = int(work_hours * 60) + break_minutes
                clock_out_dt = clock_in_dt + datetime.timedelta(minutes=total_minutes)

                # Check for existing record before creating
                if DailyTimeRecord.objects.filter(employee=profile, date=record_date).exists():
                    continue

                DailyTimeRecord.objects.create(
                    employee=profile,
                    date=record_date,
                    clock_in=clock_in_dt,
                    clock_out=clock_out_dt,
                    total_break_minutes=break_minutes,
                    status="CLOCKED_OUT",
                )

            self.stdout.write(f"  ✓ Records generated for {profile}")

        self.stdout.write(self.style.SUCCESS("\n✅ Database seeded successfully!"))
        self.stdout.write("\nLogin credentials:")
        self.stdout.write("  Employees: lisa/1234, tom/2345, klara/3456, max/4567, anna/5678")
        self.stdout.write("  HR Admin:  hr/hr1234")
