"""
URL configuration for VR_Relations project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path
from ninja import NinjaAPI
from home.api import router as home_router

api = NinjaAPI(
    title="Backend веб-приложения управления коммуникациями с клиентами клуба виртуальной реальности «Инновация Клуб»",
    version="1.0",
    description="REST API документация"
)
api.add_router("/home/", home_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", api.urls),
]

from django.urls import include
from django.urls import path
from django.views.generic import RedirectView
from home.views import CustomLoginView
urlpatterns += [
    path('home/', include('home.urls')),
    path('', RedirectView.as_view(url='/home/', permanent=True)),
    # path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
]