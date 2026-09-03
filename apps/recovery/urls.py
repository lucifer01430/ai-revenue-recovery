from django.urls import path
from . import views

app_name = 'recovery'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cases/', views.case_list, name='case_list'),
    path('cases/<uuid:case_id>/', views.case_detail, name='case_detail'),
]
