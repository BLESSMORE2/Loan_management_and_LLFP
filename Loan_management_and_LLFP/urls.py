"""
URL configuration for Loan_management_and_LLFP project.

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
from django.urls import path,include

admin.site.site_title = "Super Steak site admin (DEV)"
admin.site.site_header = "Super Steak  administration"
admin.site.index_title = "Site administration"
urlpatterns = [
   
    path('admin/', admin.site.urls),
    path('', include('IFRS9.urls')),  # Include URLs from the IFRS9 app
    path('', include('Users.urls')),
]