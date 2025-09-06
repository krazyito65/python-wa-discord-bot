"""
URL configuration for weakauras_web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication URLs (django-allauth)
    path("accounts/", include("allauth.urls")),
    # App URLs
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
    path("dashboard/", include("servers.urls")),
    path("macros/", include("macros.urls")),
    # API URLs
    path("api/", include("macros.api_urls")),
]
