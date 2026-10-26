from django.contrib.auth import views as av
from django.urls import path
from . import views as v

urlpatterns = [
    path("", v.dashboard, name="dashboard"),
    path("register/", v.register, name="register"),
    path("login/", av.LoginView.as_view(template_name="form.html", extra_context={"title": "Login"}), name="login"),
    path("logout/", av.LogoutView.as_view(), name="logout"),
    path("profile/", v.profile, name="profile"),
    path("students/", v.students, name="students"),
    path("rooms/", v.rooms, name="rooms"),
    path("rooms/request/<int:pk>/", v.request_room, name="request_room"),
    path("room-requests/", v.room_requests, name="room_requests"),
    path("room-requests/<int:pk>/<str:decision>/", v.decide_room, name="decide_room"),
    path("complaints/", v.complaints, name="complaints"),
    path("complaints/new/", v.new_complaint, name="new_complaint"),
    path("complaints/<int:pk>/advance/", v.advance_complaint, name="advance_complaint"),
    path("leaves/", v.leaves, name="leaves"),
    path("leaves/new/", v.new_leave, name="new_leave"),
    path("leaves/<int:pk>/<str:decision>/", v.decide_leave, name="decide_leave"),
    path("fees/", v.fees, name="fees"),
    path("fees/new/", v.new_fee, name="new_fee"),
]
