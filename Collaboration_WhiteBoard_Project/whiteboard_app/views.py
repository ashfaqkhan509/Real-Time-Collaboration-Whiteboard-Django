from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import (
    Board,
    BoardMembership,
    DrawingAction,
    ActiveConnection
)
from .forms import BoardForm, UserRegistrationForm, LoginForm


@login_required
def list_boards(request):
    boards = Board.objects.filter(members=request.user)
    return render(request, 'whiteboard_app/board_list.html', {'boards': boards})


@login_required
def board_detail(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    if not BoardMembership.objects.filter(board=board, user=request.user).exists():
        messages.error(request, "You do not have access to this board.")
        return redirect('list_boards')
    
    membership = BoardMembership.objects.get(board=board, user=request.user)

    can_draw = membership.permission in ["admin", "edit"]
    
    return render(request, 'whiteboard_app/board_detail.html', {
        'board': board,
        'membership': membership,
        'can_draw': can_draw,
    })



@login_required
def create_board(request):
    if request.method == 'POST':
        form = BoardForm(request.POST)
        if form.is_valid():
            board = form.save(commit=False)
            board.created_by = request.user
            board.save()
            BoardMembership.objects.create(board=board, user=request.user, permission='admin')
            messages.success(request, "Board created successfully.")
            return redirect('board_detail', board_id=board.id)
    else:
        form = BoardForm()
    
    return render(request, 'whiteboard_app/create_board.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('board_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'whiteboard_app/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Redirect to a success page or the board list
                return redirect('board_list')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'whiteboard_app/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('board_list')


@login_required
def get_board_state(request, board_id):
    board = get_object_or_404(Board, id=board_id)
    if not BoardMembership.objects.filter(board=board, user=request.user).exists():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    state = board.get_current_state()
    return JsonResponse({
        'board_id': board.id,
        'board_name': board.name,
        'state': state,

    }, status=200)