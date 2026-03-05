"""
URL configuration for My_app project.

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
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='homepage'),

    path('login/', views.login_view, name='login'),

    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),

    path('logout/', views.logout_view, name='logout'),

    path('registration/', views.registration, name='registration'),

    path('job_seeker_dashboard/', views.job_seeker_dashboard, name='job_seeker_dashboard'),

    path('employer_dashboard/', views.employer_dashboard, name='employer_dashboard'),

    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path("post_job/", views.post_job, name="post_job"),
    path('job_search/', views.job_search, name='job_search'),
    path('update_resume/', views.update_resume, name='update_resume'),
    path('manage-resume/', views.manage_resume, name='manage_resume'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('all_jobs/', views.view_all_jobs, name='view_all_jobs'),
    path('admin/', admin.site.urls),
]
 