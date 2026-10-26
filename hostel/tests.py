from django.test import TestCase
from .models import *


class HostelTests(TestCase):
    def setUp(self):
        self.warden = User.objects.create_user("w", password="x", role="warden")
        self.students = []
        for i in range(2):
            u = User.objects.create_user(f"s{i}", password="x")
            self.students.append(Student.objects.create(user=u, roll_no=f"R{i}"))
        self.room = Room.objects.create(number="1", capacity=1)

    def test_last_bed_cannot_be_double_allocated(self):
        reqs = [RoomRequest.objects.create(student=s, room=self.room) for s in self.students]
        self.client.login(username="w", password="x")
        for r in reqs:
            self.client.post(f"/room-requests/{r.pk}/approve/")
        self.assertEqual(self.room.occupancy, 1)
        self.assertEqual([RoomRequest.objects.get(pk=r.pk).status for r in reqs], ["Approved", "Pending"])

    def test_student_cannot_approve(self):
        r = RoomRequest.objects.create(student=self.students[0], room=self.room)
        self.client.login(username="s1", password="x")
        self.assertEqual(self.client.post(f"/room-requests/{r.pk}/approve/").status_code, 403)

    def test_student_sees_only_own_fees(self):
        FeeRecord.objects.create(student=self.students[0], description="Rent", amount=100)
        FeeRecord.objects.create(student=self.students[1], description="SECRET", amount=999)
        self.client.login(username="s0", password="x")
        self.assertNotContains(self.client.get("/fees/"), "SECRET")
