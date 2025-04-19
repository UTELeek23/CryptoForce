from django.urls import path
from . import views

app_name = 'crypto_force_app'

urlpatterns = [
    # Home page
    path('', views.home_view, name='home'),
    
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile URLs
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/password/change/', views.change_password_view, name='change_password'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),
    
    # Admin URLs
    path('admin/users/', views.admin_user_management, name='admin_user_management'),
    path('admin/users/<int:user_id>/toggle-status/', views.admin_toggle_user_status, name='admin_toggle_user_status'),
    path('admin/users/<int:user_id>/toggle-staff/', views.admin_toggle_user_staff, name='admin_toggle_user_staff'),
    path('admin/users/<int:user_id>/toggle-problem-setter/', views.admin_toggle_problem_setter, name='admin_toggle_problem_setter'),
    path('admin/users/<int:user_id>/toggle-contest-manager/', views.admin_toggle_contest_manager, name='admin_toggle_contest_manager'),
    
    # Problem URLs
    path('problems/create/', views.create_problem_view, name='create_problem'),
    path('problems/<int:problem_id>/edit/', views.edit_problem_view, name='edit_problem'),
    path('problems/<int:problem_id>/delete/', views.delete_problem_view, name='delete_problem'),
    path('problems/<int:problem_id>/submit/', views.submit_solution_view, name='submit_solution'),
    path('problems/<int:problem_id>/', views.problem_detail_view, name='problem_detail'),
    path('problems/', views.problem_list_view, name='problem_list'),
    path('hints/<int:hint_id>/unlock/', views.unlock_hint_view, name='unlock_hint'),
    
    # Leaderboard
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
]