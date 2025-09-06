"""
Custom authentication adapters for WeakAuras Web Interface

This module provides custom adapters to enforce Discord OAuth-only authentication
and disable traditional username/password account creation.
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect


class DiscordOnlyAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter that disables traditional account creation.

    This adapter prevents users from creating accounts through traditional
    signup forms and redirects them to Discord OAuth instead.
    """

    def is_open_for_signup(self, _request):
        """Disable traditional signup - Discord OAuth only.

        Args:
            request: Django HTTP request object.

        Returns:
            bool: Always False to disable traditional signup.
        """
        return False

    def is_safe_url(self, url):
        """Allow Discord OAuth URLs.

        Args:
            url: URL to check for safety.

        Returns:
            bool: True if URL is safe for Discord OAuth.
        """
        # Allow Discord OAuth redirect
        if "discord" in url:
            return True
        return super().is_safe_url(url)

    def get_login_redirect_url(self, _request):
        """Redirect to dashboard after Discord OAuth login.

        Args:
            request: Django HTTP request object.

        Returns:
            str: URL to redirect to after login.
        """
        return "/dashboard/"

    def respond_user_inactive(self, request, _user):
        """Handle inactive user login attempts.

        Args:
            request: Django HTTP request object.
            user: Inactive user attempting to login.

        Returns:
            HttpResponse: Redirect to Discord OAuth with error message.
        """
        messages.error(request, "Your account is inactive. Please contact support.")
        return redirect("socialaccount_login", provider="discord")


class DiscordOnlySocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for Discord OAuth.

    This adapter handles Discord-specific OAuth flow and user creation.
    """

    def is_open_for_signup(self, _request, sociallogin):
        """Allow signup only through Discord OAuth.

        Args:
            request: Django HTTP request object.
            sociallogin: Social login object containing OAuth data.

        Returns:
            bool: True only for Discord provider.
        """
        # Only allow Discord OAuth signup
        return sociallogin.account.provider == "discord"

    def populate_user(self, request, sociallogin, data):
        """Populate user data from Discord OAuth response.

        Args:
            request: Django HTTP request object.
            sociallogin: Social login object containing OAuth data.
            data: User data from Discord API.

        Returns:
            User: User object populated with Discord data.
        """
        user = super().populate_user(request, sociallogin, data)

        # Set username from Discord data
        if "username" in data:
            user.username = data["username"]
        elif "global_name" in data:
            user.username = data["global_name"]
        else:
            # Fallback to Discord user ID if no username available
            user.username = f"discord_user_{data.get('id', 'unknown')}"

        # Set display name if available
        if "global_name" in data and data["global_name"]:
            user.first_name = data["global_name"]
        elif "username" in data:
            user.first_name = data["username"]

        return user

    def save_user(self, request, sociallogin, form=None):
        """Save user account after Discord OAuth.

        Args:
            request: Django HTTP request object.
            sociallogin: Social login object containing OAuth data.
            form: Optional form data (not used for OAuth).

        Returns:
            User: Saved user object.
        """
        user = super().save_user(request, sociallogin, form)

        # Mark email as verified if provided by Discord
        if sociallogin.account.extra_data.get("email"):
            email_address, created = EmailAddress.objects.get_or_create(
                user=user,
                email=sociallogin.account.extra_data["email"],
                defaults={"verified": True, "primary": True},
            )
            if not created:
                email_address.verified = True
                email_address.save()

        return user

    def get_connect_redirect_url(self, _request, _socialaccount):
        """Redirect URL after connecting Discord account.

        Args:
            request: Django HTTP request object.
            socialaccount: Connected social account.

        Returns:
            str: URL to redirect to after account connection.
        """
        return "/dashboard/"
