from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import CustomLoginView
from registration.api_views import EventListAPI, RunnerCreateAPI

from . import views

app_name = 'registration'

urlpatterns = [
    # 🏠 Homepage: Upcoming events
    path('', views.home, name='home'),

    # 🔐 Custom admin login
    path('admin-login/', CustomLoginView.as_view(), name='admin_login'),

    # 📝 Public registration form
    path('register/', views.register_runner, name='register'),

    # AJAX: Load distances by event
    path('ajax_load_distances/', views.load_distances, name='ajax_load_distances'),

    # 📊 Admin dashboard and tools
    path('dashboard/', views.dashboard, name='dashboard'),
    path('export-xlsx/', views.export_xlsx, name='export_xlsx'),
    path('verification-stats/', views.verification_stats, name='verification_stats'),

    # 🗓️ Event CRUD
    path('event/add/', views.add_event, name='add_event'),
    path('event/<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:pk>/delete/', views.delete_event, name='delete_event'),

    # 📏 Distance management
    path('distance/add/', views.add_distance, name='add_distance'),

    # 👤 Manual runner registration (admin)
    path('runner/add/', views.manual_runner, name='manual_runner'),

    # 📃 Filtered views
    path('runners-by-event/', views.runners_by_event, name='runners_by_event'),
    path('unverified/', views.unverified_runners, name='unverified_runners'),
    path('current-events/', views.current_events, name='current_events'),

    # ✅ Verify/edit/delete runners
    path('verify/<int:pk>/', views.verify_runner, name='verify_runner'),
    path('runner/<int:pk>/edit/', views.edit_runner, name='edit_runner'),
    path('runner/<int:pk>/delete/', views.delete_runner, name='delete_runner'),
    # Edit Distances
    path('edit-distances/', views.edit_distances, name='edit_distances'),
    path('distance/<int:pk>/edit/', views.edit_distance, name='edit_distance'),
    path('distance/<int:pk>/delete/', views.delete_distance, name='delete_distance'),

    # Rest API
    path('api/events/', EventListAPI.as_view(), name='api_events'),
    path('api/register/', RunnerCreateAPI.as_view(), name='api_register'),

]

# Serve uploaded media during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


