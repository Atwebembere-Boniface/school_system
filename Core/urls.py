from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.SessionListView.as_view(), name='session_list'),
    path('sessions/add/', views.SessionCreateView.as_view(), name='session_add'),
    path('terms/add/', views.TermCreateView.as_view(), name='term_add'),
    path('settings/', views.SchoolConfigUpdateView.as_view(), name='school_settings'),
]