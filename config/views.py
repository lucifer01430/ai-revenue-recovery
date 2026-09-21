from django.http import HttpResponse


def public_home(request):
    """Public route reserved for the future landing page."""
    return HttpResponse('AI Revenue Recovery')
