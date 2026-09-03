import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
    print('Django setup successful.')
    from django.core.management import call_command
    call_command('makemigrations', interactive=False)
    call_command('migrate', interactive=False)
    print('Migrations applied.')
except Exception as e:
    import traceback
    traceback.print_exc()
