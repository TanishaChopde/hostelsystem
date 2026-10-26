from django.core.management.base import BaseCommand
from hostel.models import *

class Command(BaseCommand):
    help = "Create demo users, rooms and fees (password for all: pass1234)"

    def handle(self, *a, **k):
        for name, role in [("admin1", "admin"), ("warden1", "warden"),
                           ("maint1", "maintenance"), ("mess1", "mess")]:
            u, _ = User.objects.get_or_create(username=name, defaults={"role": role, "is_staff": role == "admin",
                                                                       "is_superuser": role == "admin"})
            u.set_password("pass1234"); u.save()
        for i, name in enumerate(["student1", "student2"], 1):
            u, _ = User.objects.get_or_create(username=name, defaults={"first_name": name.title()})
            u.set_password("pass1234"); u.save()
            Student.objects.get_or_create(user=u, defaults={"roll_no": f"2024{i:03d}", "course": "B.Tech CSE"})
        for n, cap in [("101", 2), ("102", 2), ("103", 1), ("104", 3)]:
            Room.objects.get_or_create(number=n, defaults={"capacity": cap})
        self.stdout.write("Seeded. Log in as admin1 / warden1 / maint1 / mess1 / student1 / student2 (pass1234)")
