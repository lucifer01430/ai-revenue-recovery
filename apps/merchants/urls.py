from django.urls import path

from . import views

urlpatterns = [
    path('setup/', views.setup, name='merchant_setup'),
    path('settings/', views.profile, name='merchant_profile'),
]
