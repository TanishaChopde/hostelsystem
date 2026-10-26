from functools import wraps
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import *
from .models import *

STAFF = ("warden", "admin")


def roles(*allowed):
    def deco(f):
        @login_required
        @wraps(f)
        def w(request, *a, **k):
            if request.user.role not in allowed:
                raise PermissionDenied
            return f(request, *a, **k)
        return w
    return deco


def table(request, title, cols, rows, add=None):
    return render(request, "table.html", {"title": title, "cols": cols, "rows": rows, "add": add})


def row(cells, actions=()):
    return {"cells": cells, "actions": actions}


def form_view(request, form_cls, title, done, on_valid, instance_kw=None):
    form = form_cls(request.POST or None)
    if request.method == "POST" and form.is_valid():
        on_valid(form)
        return redirect(done)
    return render(request, "form.html", {"form": form, "title": title})


# ---------- FR1 accounts ----------
def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")
    return render(request, "form.html", {"form": form, "title": "Student Registration"})


@roles("student")
def profile(request):
    s = request.user.student
    form = ProfileForm(request.POST or None, instance=s)
    if request.method == "POST" and form.is_valid():
        form.save(); messages.success(request, "Profile updated."); return redirect("dashboard")
    return render(request, "form.html", {"form": form, "title": "Update Profile"})


@roles(*STAFF)
def students(request):
    rows = [row([s.roll_no, s.user.get_full_name() or s.user.username, s.course, s.phone, s.room or "-"])
            for s in Student.objects.select_related("user")]
    return table(request, "Students", ["Roll", "Name", "Course", "Phone", "Room"], rows)


# ---------- FR10 dashboard ----------
def recent_items(u):
    """Latest requests/complaints as (time, kind, who, status) for the activity feed."""
    mine = u.student if u.role == "student" else None
    kinds = [(Complaint, "Complaint")]
    if u.role not in ("mess", "maintenance"):
        kinds += [(LeaveRequest, "Leave request"), (RoomRequest, "Room request")]
    items = []
    for model, label in kinds:
        qs = model.objects.select_related("student__user").order_by("-created")
        if mine:
            qs = qs.filter(student=mine)
        elif u.role in ("mess", "maintenance"):
            qs = qs.filter(category="Mess" if u.role == "mess" else "Maintenance")
        items += [(o.created, label, "" if mine else str(o.student), o.status) for o in qs[:4]]
    return sorted(items, key=lambda x: x[0], reverse=True)[:6]


@login_required
def dashboard(request):
    u = request.user
    if u.role == "student":
        s = u.student
        dues = sum(f.due for f in s.feerecord_set.all())
        cards = [("My room", s.room or "Not allocated"),
                 ("Pending room requests", s.roomrequest_set.filter(status="Pending").count()),
                 ("Open complaints", s.complaint_set.exclude(status="Resolved").count()),
                 ("Pending leave requests", s.leaverequest_set.filter(status="Pending").count()),
                 ("Outstanding dues (INR)", dues)]
    else:
        cap = Room.objects.aggregate(c=Sum("capacity"))["c"] or 0
        occ = Allocation.objects.filter(released_at__isnull=True).count()
        cards = [("Students", Student.objects.count()), ("Occupancy", f"{occ}/{cap}"),
                 ("Pending room requests", RoomRequest.objects.filter(status="Pending").count()),
                 ("Pending complaints", Complaint.objects.filter(status="Pending").count()),
                 ("Pending leave requests", LeaveRequest.objects.filter(status="Pending").count())]
    return render(request, "dashboard.html", {"cards": cards, "recent": recent_items(u)})


# ---------- FR2 rooms ----------
@login_required
def rooms(request):
    is_student = request.user.role == "student"
    data = []
    for r in Room.objects.all():
        occ = r.occupancy
        free = r.available and occ < r.capacity
        data.append({"pk": r.pk, "number": r.number, "capacity": r.capacity, "occ": occ,
                     "pct": int(occ * 100 / r.capacity) if r.capacity else 0,
                     "free": free, "can_request": is_student and free})
    return render(request, "rooms.html", {"rooms": data})


@roles("student")
def request_room(request, pk):
    if request.method == "POST":
        s, room = request.user.student, get_object_or_404(Room, pk=pk)
        if s.room:
            messages.error(request, "You already have an allocated room.")
        elif s.roomrequest_set.filter(status="Pending").exists():
            messages.error(request, "You already have a pending room request.")
        elif not room.available or room.occupancy >= room.capacity:
            messages.error(request, "That room is not available.")
        else:
            RoomRequest.objects.create(student=s, room=room)
            messages.success(request, "Room request submitted.")
    return redirect("room_requests")


@login_required
def room_requests(request):
    qs = RoomRequest.objects.select_related("student__user", "room").order_by("-created")
    staff = request.user.role in STAFF
    if request.user.role == "student":
        qs = qs.filter(student=request.user.student)
    elif not staff:
        raise PermissionDenied
    rows = []
    for r in qs:
        acts = [("Approve", f"/room-requests/{r.pk}/approve/"),
                ("Reject", f"/room-requests/{r.pk}/reject/")] if staff and r.status == "Pending" else []
        rows.append(row([r.student, r.room, r.status, r.created.strftime("%d %b %Y")], acts))
    return table(request, "Room Requests", ["Student", "Room", "Status", "Date"], rows)


@roles(*STAFF)
def decide_room(request, pk, decision):
    """Approval is atomic: rows are locked, capacity re-checked, allocation + status committed together."""
    if request.method == "POST" and decision in ("approve", "reject"):
        with transaction.atomic():
            rr = RoomRequest.objects.select_for_update().get(pk=pk)
            room = Room.objects.select_for_update().get(pk=rr.room_id)
            if rr.status != "Pending":
                messages.error(request, "Request already processed.")
            elif decision == "reject":
                rr.status, rr.decided_by = "Rejected", request.user
                rr.save(); messages.info(request, "Request rejected.")
            elif rr.student.room:
                messages.error(request, "Student already has an active allocation.")
            elif not room.available or room.occupancy >= room.capacity:
                messages.error(request, "Conflict: room is full. Request kept Pending for review.")
            else:
                Allocation.objects.create(student=rr.student, room=room, request=rr)
                rr.status, rr.decided_by = "Approved", request.user
                rr.save(); messages.success(request, "Request approved and room allocated.")
    return redirect("room_requests")


# ---------- FR3/FR4/FR9 complaints ----------
@roles("student")
def new_complaint(request):
    def save(form):
        c = form.save(commit=False)
        c.student = request.user.student
        role = {"Mess": "mess", "Maintenance": "maintenance"}.get(c.category)
        c.assigned_to = User.objects.filter(role=role).first() if role else None
        c.save(); messages.success(request, "Complaint registered.")
    return form_view(request, ComplaintForm, "New Complaint", "complaints", save)


@login_required
def complaints(request):
    u = request.user
    qs = Complaint.objects.select_related("student__user", "assigned_to").order_by("-created")
    scope = {"student": {"student": getattr(u, "student", None)}, "mess": {"category": "Mess"},
             "maintenance": {"category": "Maintenance"}}.get(u.role, {})
    qs = qs.filter(**scope)
    rows = []
    for c in qs:
        acts = [(f"Mark {Complaint.NEXT[c.status]}", f"/complaints/{c.pk}/advance/")] \
            if u.role != "student" and c.status in Complaint.NEXT else []
        rows.append(row([c.student, c.category, c.meal_type or c.issue_type or "-", c.description,
                         c.status, c.assigned_to or "-"], acts))
    add = ("/complaints/new/", "New complaint") if u.role == "student" else None
    return table(request, "Complaints", ["Student", "Category", "Type", "Description", "Status", "Assigned"], rows, add)


@roles("warden", "admin", "maintenance", "mess")
def advance_complaint(request, pk):
    c = get_object_or_404(Complaint, pk=pk)
    u = request.user
    allowed = u.role in STAFF or (u.role == "mess" and c.category == "Mess") or \
              (u.role == "maintenance" and c.category == "Maintenance")
    if not allowed:
        raise PermissionDenied
    if request.method == "POST" and c.status in Complaint.NEXT:  # only Pending->In Progress->Resolved
        c.status = Complaint.NEXT[c.status]; c.save()
    return redirect("complaints")


# ---------- FR5 leave / out-pass ----------
@roles("student")
def new_leave(request):
    def save(form):
        l = form.save(commit=False); l.student = request.user.student; l.save()
        messages.success(request, "Leave request submitted.")
    return form_view(request, LeaveForm, "New Leave / Out-Pass Request", "leaves", save)


@login_required
def leaves(request):
    qs = LeaveRequest.objects.select_related("student__user").order_by("-created")
    if request.user.role == "student":
        qs = qs.filter(student=request.user.student)
    elif request.user.role != "warden" and request.user.role != "admin":
        raise PermissionDenied
    rows = []
    for l in qs:
        acts = [("Approve", f"/leaves/{l.pk}/approve/"), ("Reject", f"/leaves/{l.pk}/reject/")] \
            if request.user.role == "warden" and l.status == "Pending" else []
        rows.append(row([l.student, l.departure, l.return_date, l.reason, l.status], acts))
    add = ("/leaves/new/", "New request") if request.user.role == "student" else None
    return table(request, "Leave / Out-Pass Requests", ["Student", "Departure", "Return", "Reason", "Status"], rows, add)


@roles("warden")  # only wardens approve leave
def decide_leave(request, pk, decision):
    l = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == "POST" and l.status == "Pending" and decision in ("approve", "reject"):
        l.status = "Approved" if decision == "approve" else "Rejected"
        l.decided_by = request.user; l.save()
    return redirect("leaves")


# ---------- FR6 fees ----------
@login_required
def fees(request):
    qs = FeeRecord.objects.select_related("student__user")
    if request.user.role == "student":
        qs = qs.filter(student=request.user.student)
    elif request.user.role not in STAFF:
        raise PermissionDenied
    rows = [row([f.student, f.description, f.amount, f.paid, f.due, f.status]) for f in qs]
    add = ("/fees/new/", "Add fee record") if request.user.role == "admin" else None
    return table(request, "Fees & Dues", ["Student", "Description", "Amount", "Paid", "Due", "Status"], rows, add)


@roles("admin")
def new_fee(request):
    def save(form):
        f = form.save(commit=False); f.updated_by = request.user; f.save()
    return form_view(request, FeeForm, "Add Fee Record", "fees", save)
