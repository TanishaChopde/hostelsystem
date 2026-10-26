from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *

DATE = forms.DateInput(attrs={"type": "date"})


class RegisterForm(UserCreationForm):
    roll_no = forms.CharField(max_length=20)
    phone = forms.CharField(max_length=15, required=False)
    course = forms.CharField(max_length=60, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "email")

    def clean_roll_no(self):
        r = self.cleaned_data["roll_no"]
        if Student.objects.filter(roll_no=r).exists():
            raise forms.ValidationError("Roll number already registered.")
        return r

    def save(self, commit=True):
        u = super().save(commit)
        Student.objects.create(user=u, roll_no=self.cleaned_data["roll_no"],
                               phone=self.cleaned_data["phone"], course=self.cleaned_data["course"])
        return u


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ("phone", "course")


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("category", "description", "meal_type", "issue_type")

    def clean(self):
        d = super().clean()
        if d.get("category") == "Mess" and not d.get("meal_type"):
            self.add_error("meal_type", "Required for mess complaints (e.g. Lunch).")
        if d.get("category") == "Maintenance" and not d.get("issue_type"):
            self.add_error("issue_type", "Required for maintenance complaints (e.g. Plumbing).")
        return d


class LeaveForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ("departure", "return_date", "reason")
        widgets = {"departure": DATE, "return_date": DATE}

    def clean(self):
        d = super().clean()
        if d.get("departure") and d.get("return_date") and d["return_date"] < d["departure"]:
            self.add_error("return_date", "Return date cannot be before departure.")
        return d


class FeeForm(forms.ModelForm):
    class Meta:
        model = FeeRecord
        fields = ("student", "description", "amount", "paid")

    def clean(self):
        d = super().clean()
        if d.get("amount") is not None and d.get("paid") is not None and d["paid"] > d["amount"]:
            self.add_error("paid", "Paid amount cannot exceed total amount.")
        return d
