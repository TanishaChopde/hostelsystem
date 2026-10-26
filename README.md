# Hostel Management System (CSE3132)
Django implementation of Phases 1-3 (FR1-FR10).

    pip install django
    python manage.py migrate
    python manage.py seed          # demo users, password pass1234
    python manage.py runserver     # http://127.0.0.1:8000
    python manage.py test          # access-control & room-allocation checks

Demo logins: admin1, warden1, maint1, mess1, student1, student2.
Layout: hostel/models.py = Phase 3 DB model; views.py = business rules (atomic room approval,
complaint state transitions, role checks); templates/ = UI. Admin panel: /admin/ (admin1).
