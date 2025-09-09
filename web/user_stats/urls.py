"""
URL configuration for user_stats app.

This module handles user statistics views for the WeakAuras web interface.
"""

from django.urls import path

from . import views

app_name = "user_stats"

urlpatterns = [
    # Dashboard - shows all guilds with statistics
    path("", views.user_stats_dashboard, name="dashboard"),
    # Guild statistics - shows users and their message counts for a specific guild
    path("<int:guild_id>/", views.guild_user_stats, name="guild_stats"),
    # User detail - detailed view for a specific user in a guild
    path(
        "<int:guild_id>/user/<str:user_id>/",
        views.user_detail_stats,
        name="user_detail",
    ),
    # API endpoint for JSON data
    path("api/<int:guild_id>/", views.api_guild_stats_json, name="api_guild_stats"),
    # Live updates endpoint for real-time progress
    path("api/<int:guild_id>/live/", views.live_stats_update, name="live_stats_update"),
]
