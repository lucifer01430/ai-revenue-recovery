
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, reverse_lazy
from apps.payments.views import razorpay_webhook
from apps.merchants.views import profile as merchant_profile
from .views import public_home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.txt',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html', success_url=reverse_lazy('password_reset_complete')), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html', success_url=reverse_lazy('password_change_done')), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    path('merchant/', include('apps.merchants.urls')),
    path('app/settings/', merchant_profile, name='merchant_profile'),
    path('api/payments/', include('apps.payments.urls')),
    path('webhooks/razorpay/', razorpay_webhook, name='razorpay_webhook'),
    path('app/', include('apps.recovery.urls')),
    path('', public_home, name='public_home'),
]
