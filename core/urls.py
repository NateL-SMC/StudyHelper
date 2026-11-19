from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # auth
    path("signin/", views.SignInView.as_view(), name="login"),
    path("signup/", views.signup, name="signup"),
    path("signout/", auth_views.LogoutView.as_view(), name="logout"),

    # forgot password (4 built-in steps)
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt",
        success_url=reverse_lazy("password_reset_done")), name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/message.html",
        extra_context={"heading": "Check your email",
                       "text": "If an account exists for that email, a reset link has been sent. "
                               "(In development the link is printed in the terminal running the server.)"}),
        name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html",
        success_url=reverse_lazy("password_reset_complete")), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/message.html",
        extra_context={"heading": "Password changed", "text": "You can now sign in with your new password."}),
        name="password_reset_complete"),

    # student
    path("dashboard/", views.dashboard, name="dashboard"),
    path("tasks/<int:pk>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("profile/city/", views.set_city, name="set_city"),

    # JSON API proxies
    path("api/quote/", views.api_quote, name="api_quote"),
    path("api/weather/", views.api_weather, name="api_weather"),
    path("api/books/", views.api_books, name="api_books"),
    path("api/define/", views.api_define, name="api_define"),
    path("api/videos/", views.api_videos, name="api_videos"),

    # admin
    path("manage/", views.admin_dashboard, name="admin_dashboard"),
    path("manage/users/<int:pk>/role/", views.admin_user_role, name="admin_user_role"),
    path("manage/users/<int:pk>/active/", views.admin_user_active, name="admin_user_active"),
    path("manage/users/<int:pk>/delete/", views.admin_user_delete, name="admin_user_delete"),
    path("manage/tasks/<int:pk>/delete/", views.admin_task_delete, name="admin_task_delete"),
]
