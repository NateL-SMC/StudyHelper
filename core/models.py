from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_STUDENT = "student"
    ROLE_CHOICES = [(ROLE_ADMIN, "Admin"), (ROLE_STUDENT, "Student")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    city = models.CharField(max_length=80, blank=True, help_text="Used for the weather widget")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Task(models.Model):
    PRIORITY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]
    STATUS_CHOICES = [("todo", "To do"), ("doing", "In progress"), ("done", "Done")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="todo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "due_date", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return bool(self.due_date and self.status != "done" and self.due_date < timezone.localdate())
