"""
URL configuration for the admin panel app.
"""

from django.urls import path

from . import views

app_name = "admin_panel"

urlpatterns = [
    path("<int:guild_id>/", views.admin_panel_dashboard, name="dashboard"),
    path(
        "<int:guild_id>/permissions/",
        views.permission_settings,
        name="permission_settings",
    ),
    path("<int:guild_id>/roles/", views.role_settings, name="role_settings"),
    path("<int:guild_id>/audit/", views.audit_log, name="audit_log"),
    path("<int:guild_id>/reset/", views.reset_to_defaults, name="reset_to_defaults"),
]
