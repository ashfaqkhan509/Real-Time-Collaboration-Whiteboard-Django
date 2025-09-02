from django.urls import path, include
from . import views


urlpatterns = [
    # Define your URL patterns here
    path('', views.list_boards, name='board_list'),
    path('board/<int:board_id>/', views.board_detail, name='board_detail'),
    path('board/create/', views.create_board, name='create_board'),
    path('board/<int:board_id>/state/', views.get_board_state, name='get_board_state'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
