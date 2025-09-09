"""
URL configuration for servers app.

This module handles server selection and dashboard views for the WeakAuras web interface.
"""

from django.urls import path

from . import views

app_name = "servers"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("select/", views.server_select, name="server_select"),
    path("server/<int:guild_id>/", views.server_hub, name="server_hub"),
    path("server/<int:guild_id>/macros/", views.server_detail, name="server_detail"),
]
