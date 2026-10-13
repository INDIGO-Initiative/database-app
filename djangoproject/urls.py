"""djangoproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
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
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from indigo.forms import StyledAuthenticationForm

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "accounts/login/",
        LoginView.as_view(authentication_form=StyledAuthenticationForm),
        name="login",
    ),
    # Django's admin app has its own logged_out.html that would win over ours, so ours is named differently
    path(
        "accounts/logout/",
        LogoutView.as_view(template_name="indigo/logged_out.html"),
        name="logout",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    # The JSON Data Ferret library has web pages of its own (event and record lists, a record edit form and so on). We
    # do not use them: the app has its own admin pages that apply our permissions and validation. So they are not
    # included here, and old links to them go to the admin home page instead.
    path(
        "jsondataferret/",
        views.RetiredPageRedirect.as_view(),
        name="jsondataferret_retired",
    ),
    path(
        "jsondataferret/<path:rest>",
        views.RetiredPageRedirect.as_view(),
        name="jsondataferret_retired_path",
    ),
    path("app/", include("indigo.urls")),
    path("admin/", admin.site.urls),
]
