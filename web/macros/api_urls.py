"""
API URL configuration for macros app.

This module handles REST API endpoints for macro management.
"""

from django.urls import path

from . import api_views

app_name = "macros_api"

urlpatterns = [
    path("servers/", api_views.ServerListAPIView.as_view(), name="server_list"),
    path(
        "servers/<int:guild_id>/macros/",
        api_views.MacroListAPIView.as_view(),
        name="macro_list",
    ),
    path(
        "servers/<int:guild_id>/macros/add/",
        api_views.MacroCreateAPIView.as_view(),
        name="macro_create",
    ),
    path(
        "servers/<int:guild_id>/macros/<str:macro_name>/",
        api_views.MacroDetailAPIView.as_view(),
        name="macro_detail",
    ),
]
