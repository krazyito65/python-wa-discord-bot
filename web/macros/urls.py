"""
URL configuration for macros app.

This module handles macro management views for the WeakAuras web interface.
"""

from django.urls import path

from . import views

app_name = "macros"

urlpatterns = [
    path("<int:guild_id>/", views.macro_list, name="macro_list"),
    path("<int:guild_id>/add/", views.macro_add, name="macro_add"),
    path("<int:guild_id>/get/<str:macro_name>/", views.macro_get, name="macro_get"),
    path("<int:guild_id>/edit/<str:macro_name>/", views.macro_edit, name="macro_edit"),
    path(
        "<int:guild_id>/delete/<str:macro_name>/",
        views.macro_delete,
        name="macro_delete",
    ),
]
