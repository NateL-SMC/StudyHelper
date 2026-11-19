from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Case, Count, F, IntegerField, Q, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import services
from .forms import SignUpForm, TaskForm
from .models import Profile, Task

User = get_user_model()


# ------------------------------------------------------------------ helpers
def is_admin(user):
    return user.is_authenticated and hasattr(user, "profile") and user.profile.role == Profile.ROLE_ADMIN


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "Admins only.")
            return redirect("dashboard")
        return view(request, *args, **kwargs)
    return wrapper


def home_for(user):
    return "admin_dashboard" if is_admin(user) else "dashboard"


# ------------------------------------------------------------------ auth
def home(request):
    if request.user.is_authenticated:
        return redirect(home_for(request.user))
    return redirect("login")


class SignInView(LoginView):
    template_name = "signin.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        from django.urls import reverse
        return reverse(home_for(self.request.user))


def signup(request):
    if request.user.is_authenticated:
        return redirect(home_for(request.user))
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account is ready.")
        return redirect("dashboard")
    return render(request, "signup.html", {"form": form})


# ------------------------------------------------------------------ student dashboard + task CRUD
@login_required
def dashboard(request):
    # CREATE
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, "Task added.")
            return redirect("dashboard")
    else:
        form = TaskForm()

    # READ
    all_tasks = request.user.tasks.annotate(
        finished=Case(When(status="done", then=1), default=0, output_field=IntegerField())
    ).order_by("finished", F("due_date").asc(nulls_last=True), "-created_at")
    status = request.GET.get("status", "")
    tasks = all_tasks.filter(status=status) if status in ("todo", "doing", "done") else all_tasks
    today = timezone.localdate()
    stats = all_tasks.aggregate(
        todo=Count("id", filter=Q(status="todo")),
        doing=Count("id", filter=Q(status="doing")),
        done=Count("id", filter=Q(status="done")),
        overdue=Count("id", filter=~Q(status="done") & Q(due_date__lt=today)),
    )
    return render(request, "dashboard.html", {
        "form": form, "tasks": tasks, "stats": stats, "status": status,
        "city": request.user.profile.city,
    })


@login_required
def task_edit(request, pk):  # UPDATE
    task = get_object_or_404(Task, pk=pk, user=request.user)
    form = TaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Task updated.")
        return redirect("dashboard")
    return render(request, "task_edit.html", {"form": form, "task": task})


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.status = "todo" if task.status == "done" else "done"
    task.save()
    return redirect("dashboard")


@login_required
@require_POST
def task_delete(request, pk):  # DELETE
    get_object_or_404(Task, pk=pk, user=request.user).delete()
    messages.success(request, "Task deleted.")
    return redirect("dashboard")


@login_required
@require_POST
def set_city(request):
    city = request.POST.get("city", "").strip()[:80]
    if city:
        request.user.profile.city = city
        request.user.profile.save()
    return redirect("dashboard")


# ------------------------------------------------------------------ JSON endpoints (proxy the free APIs)
def _api(fn, *args):
    try:
        return JsonResponse({"ok": True, "data": fn(*args)})
    except services.ApiError as exc:
        return JsonResponse({"ok": False, "error": str(exc)})


@login_required
@require_GET
def api_quote(request):
    return JsonResponse({"ok": True, "data": services.daily_quote()})


@login_required
@require_GET
def api_weather(request):
    return _api(services.weather_for_city, request.user.profile.city)


@login_required
@require_GET
def api_books(request):
    q = request.GET.get("q", "").strip()
    return _api(services.search_books, q) if q else JsonResponse({"ok": False, "error": "Enter a search term."})


@login_required
@require_GET
def api_define(request):
    return _api(services.define_word, request.GET.get("q", ""))


@login_required
@require_GET
def api_videos(request):
    q = request.GET.get("q", "").strip()
    return _api(services.search_videos, q) if q else JsonResponse({"ok": False, "error": "Enter a search term."})


# ------------------------------------------------------------------ admin dashboard
@admin_required
def admin_dashboard(request):
    today = timezone.localdate()
    tasks = Task.objects.all()
    total = tasks.count()
    done = tasks.filter(status="done").count()
    stats = {
        "users": User.objects.count(),
        "students": Profile.objects.filter(role=Profile.ROLE_STUDENT).count(),
        "admins": Profile.objects.filter(role=Profile.ROLE_ADMIN).count(),
        "tasks": total,
        "overdue": tasks.exclude(status="done").filter(due_date__lt=today).count(),
        "completion": round(done / total * 100) if total else 0,
    }
    by_status = [
        {"label": label, "count": tasks.filter(status=key).count(), "key": key}
        for key, label in Task.STATUS_CHOICES
    ]
    for row in by_status:
        row["pct"] = round(row["count"] / total * 100) if total else 0
    users = User.objects.select_related("profile").annotate(task_count=Count("tasks")).order_by("-date_joined")
    return render(request, "admin_dashboard.html", {
        "stats": stats, "by_status": by_status, "users": users,
        "recent_tasks": tasks.select_related("user").order_by("-created_at")[:20],
    })


@admin_required
@require_POST
def admin_user_role(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You can't change your own role.")
    else:
        p = user.profile
        p.role = Profile.ROLE_STUDENT if p.role == Profile.ROLE_ADMIN else Profile.ROLE_ADMIN
        p.save()
        messages.success(request, f"{user.username} is now {p.get_role_display()}.")
    return redirect("admin_dashboard")


@admin_required
@require_POST
def admin_user_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You can't deactivate yourself.")
    else:
        user.is_active = not user.is_active
        user.save()
        messages.success(request, f"{user.username} {'activated' if user.is_active else 'deactivated'}.")
    return redirect("admin_dashboard")


@admin_required
@require_POST
def admin_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You can't delete yourself.")
    else:
        user.delete()
        messages.success(request, "User deleted.")
    return redirect("admin_dashboard")


@admin_required
@require_POST
def admin_task_delete(request, pk):
    get_object_or_404(Task, pk=pk).delete()
    messages.success(request, "Task deleted.")
    return redirect("admin_dashboard")
