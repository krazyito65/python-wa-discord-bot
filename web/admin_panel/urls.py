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
    path(
        "<int:guild_id>/assignable-roles/",
        views.manage_assignable_roles,
        name="manage_assignable_roles",
    ),
    path(
        "<int:guild_id>/assignable-roles/add/",
        views.add_assignable_role,
        name="add_assignable_role",
    ),
    path(
        "<int:guild_id>/assignable-roles/remove/<str:role_id>/",
        views.remove_assignable_role,
        name="remove_assignable_role",
    ),
    path(
        "<int:guild_id>/events/",
        views.manage_events,
        name="manage_events",
    ),
    path(
        "<int:guild_id>/events/toggle/<str:event_type>/",
        views.toggle_event,
        name="toggle_event",
    ),
    path("<int:guild_id>/audit/", views.audit_log, name="audit_log"),
    path("<int:guild_id>/reset/", views.reset_to_defaults, name="reset_to_defaults"),
]
