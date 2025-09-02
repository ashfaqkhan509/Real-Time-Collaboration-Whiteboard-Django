from celery import Celery
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Collaboration_WhiteBoard_Project.settings')

app = Celery('Collaboration_WhiteBoard_Project')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()