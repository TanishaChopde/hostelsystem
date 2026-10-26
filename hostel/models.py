from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, Sum, F


class User(AbstractUser):
    ROLES = [("student", "Student"), ("warden", "Warden"), ("admin", "Hostel Administrator"),
             ("maintenance", "Maintenance Staff"), ("mess", "Mess Staff")]
    role = models.CharField(max_length=12, choices=ROLES, default="student")


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roll_no = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15, blank=True)
    course = models.CharField(max_length=60, blank=True)

    @property
    def room(self):
        a = self.allocation_set.filter(released_at__isnull=True).select_related("room").first()
        return a.room if a else None

    def __str__(self):
        return f"{self.roll_no} - {self.user.get_full_name() or self.user.username}"


class Room(models.Model):
    number = models.CharField(max_length=10, unique=True)
    capacity = models.PositiveSmallIntegerField(default=2)
    available = models.BooleanField(default=True)

    @property
    def occupancy(self):
        return self.allocation_set.filter(released_at__isnull=True).count()

    def __str__(self):
        return f"Room {self.number}"


class RoomRequest(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, default="Pending")  # Pending/Approved/Rejected
    created = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)


class Allocation(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    request = models.OneToOneField(RoomRequest, null=True, on_delete=models.SET_NULL)
    allocated_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # a student may have only one active allocation
        constraints = [models.UniqueConstraint(fields=["student"], condition=Q(released_at__isnull=True),
                                               name="one_active_allocation_per_student")]


class Complaint(models.Model):
    CATEGORIES = [("General", "General"), ("Mess", "Mess"), ("Maintenance", "Maintenance")]
    NEXT = {"Pending": "In Progress", "In Progress": "Resolved"}
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    category = models.CharField(max_length=12, choices=CATEGORIES)
    description = models.TextField()
    meal_type = models.CharField(max_length=20, blank=True)    # Mess only
    issue_type = models.CharField(max_length=30, blank=True)   # Maintenance only
    status = models.CharField(max_length=12, default="Pending")
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="assigned_complaints")
    created = models.DateTimeField(auto_now_add=True)


class LeaveRequest(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    departure = models.DateField()
    return_date = models.DateField()
    reason = models.CharField(max_length=200)
    status = models.CharField(max_length=10, default="Pending")  # Pending/Approved/Rejected
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)


class FeeRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def due(self):
        return self.amount - self.paid

    @property
    def status(self):
        return "Paid" if self.due <= 0 else "Due"
