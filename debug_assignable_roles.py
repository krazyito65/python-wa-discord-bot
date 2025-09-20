#!/usr/bin/env python3
"""Debug script to check assignable roles in database."""

import os
import sys

import django

# Add the web directory to Python path
sys.path.insert(0, "web")

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "weakauras_web.production_debug")
os.environ.setdefault("DJANGO_SECRET_KEY", "dummy")
django.setup()

from admin_panel.models import AssignableRole, ServerPermissionConfig  # noqa: E402


def check_assignable_roles(guild_id=None):
    """Check assignable roles in database."""
    if guild_id:
        print(f"🔍 Checking assignable roles for guild {guild_id}...")
        try:
            server_config = ServerPermissionConfig.objects.get(guild_id=str(guild_id))
        except ServerPermissionConfig.DoesNotExist:
            print(f"❌ No server config found for guild {guild_id}")
            return
    else:
        print("🔍 Checking all assignable roles...")

    if guild_id:
        roles = AssignableRole.objects.filter(server_config=server_config).order_by(
            "-created_at"
        )
    else:
        roles = AssignableRole.objects.all().order_by("-created_at")

    if not roles:
        print("❌ No assignable roles found")
        return

    print(f"📊 Found {len(roles)} assignable roles:")
    print()

    for role in roles:
        print(f"🎭 Role: {role.role_name}")
        print(f"   ID: {role.role_id}")
        print(
            f"   Server: {role.server_config.guild_name} ({role.server_config.guild_id})"
        )
        print(f"   Self Assignable: {'✅ YES' if role.is_self_assignable else '❌ NO'}")
        print(f"   Requires Permission: {role.requires_permission}")
        print(f"   Color: {role.role_color}")
        print(f"   Added: {role.created_at}")
        print(f"   Added by: {role.added_by_name}")
        print()


EXPECTED_ARGS = 2

if __name__ == "__main__":
    if len(sys.argv) == EXPECTED_ARGS:
        guild_id = sys.argv[1]
        check_assignable_roles(guild_id)
    else:
        print("Usage: python debug_assignable_roles.py [guild_id]")
        print("       python debug_assignable_roles.py 172440238717665280")
        print()
        check_assignable_roles()
