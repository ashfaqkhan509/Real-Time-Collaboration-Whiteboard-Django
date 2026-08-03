from django.contrib import admin
from .models import Board, BoardMembership, DrawingAction, BoardSnapshot, ActiveConnection


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']


@admin.register(BoardMembership)
class BoardMembershipAdmin(admin.ModelAdmin):
    list_display = ['board', 'user', 'permission', 'joined_at']
    list_filter = ['permission', 'joined_at']


@admin.register(DrawingAction)
class DrawingActionAdmin(admin.ModelAdmin):
    list_display = ['board', 'user', 'action_type', 'created_at']
    list_filter = ['action_type', 'created_at']
    readonly_fields = ['action_data']


@admin.register(ActiveConnection)
class ActiveConnectionAdmin(admin.ModelAdmin):
    list_display = ['board', 'user', 'connected_at', 'last_seen']
    list_filter = ['connected_at']


@admin.register(BoardSnapshot)
class BoardSnapshotAdmin(admin.ModelAdmin):
    list_display = ['board', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['snapshot_data']
