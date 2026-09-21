from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django import forms

from .models import Merchant


def merchant_for_user(user):
    if not user.is_authenticated:
        return None
    return Merchant.objects.filter(owner=user, is_active=True).first()


class MerchantProfileForm(forms.ModelForm):
    class Meta:
        model = Merchant
        fields = ('name', 'email')
        labels = {'name': 'Business name', 'email': 'Operations email'}


@login_required
def setup(request):
    merchant = merchant_for_user(request.user)
    if merchant:
        return redirect('recovery:dashboard')
    if request.method == 'POST':
        form = MerchantProfileForm(request.POST)
        if form.is_valid():
            merchant = form.save(commit=False)
            merchant.owner = request.user
            merchant.razorpay_key_id = settings.RAZORPAY_KEY_ID
            merchant.razorpay_key_secret = settings.RAZORPAY_KEY_SECRET
            merchant.is_active = True
            merchant.save()
            return redirect('recovery:dashboard')
    else:
        form = MerchantProfileForm(initial={'email': request.user.email})
    return render(request, 'merchants/setup.html', {'form': form, 'mode': 'setup'})


@login_required
def profile(request):
    merchant = merchant_for_user(request.user)
    if not merchant:
        return redirect('merchant_setup')
    if request.method == 'POST':
        form = MerchantProfileForm(request.POST, instance=merchant)
        if form.is_valid():
            form.save()
            return redirect('recovery:dashboard')
    else:
        form = MerchantProfileForm(instance=merchant)
    return render(request, 'merchants/setup.html', {'form': form, 'merchant': merchant, 'mode': 'profile'})
