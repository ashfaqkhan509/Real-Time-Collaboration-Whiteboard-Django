from django.db import models
from django.contrib.auth.models import User


class Board(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    members = models.ManyToManyField(User, through='BoardMembership', related_name='boards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_current_state(self):
        actions = self.drawing_actions.all().order_by('created_at')
        state = []
        for action in actions:
            state.append({
                'id': action.id,
                'action_type': action.action_type,
                'action_data': action.action_data,
                'action_id': action.action_id,
                'timestamp': str(action.created_at)
            })
        return state


class BoardMembership(models.Model):
    PERMISION_CHOICES = [
        ('view', 'View Only'),
        ('edit', 'Edit'),
        ('admin', 'Admin'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    board = models.ForeignKey(Board, on_delete=models.CASCADE)
    permission = models.CharField(max_length=10, choices=PERMISION_CHOICES, default='view')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'board')

    def __str__(self):
        return f"{self.user.username} in {self.board.name}"


class DrawingAction(models.Model):
    ACTION_TYPES = [
        ('draw', 'Draw'),
        ('shape', 'Shape'),
        ('text', 'Text'),
        ('erase', 'Erase'),
        ('clear', 'Clear'),
    ]

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='drawing_actions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    action_data = models.JSONField()  # Details of the action (coordinates, color, etc.)
    created_at = models.DateTimeField(auto_now_add=True)
    action_id = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.action_type} by {self.user.username} on {self.board.name}"


class BoardSnapshot(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='snapshots')
    snapshot_data = models.JSONField()  # Full board state
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Snapshot of {self.board.name} at {self.created_at}"


class ActiveConnection(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='active_connections')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel_name = models.CharField(max_length=200)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['board', 'user']

    def __str__(self):
        return f"{self.user.username} connected to {self.board.name}"
