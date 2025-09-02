from django.urls import path
from whiteboard_app import consumers


websocket_urlpatterns = [
    path('ws/board/<int:board_id>/', consumers.WhiteboardConsumer.as_asgi()),
]
