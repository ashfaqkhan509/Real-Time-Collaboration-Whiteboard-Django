import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Board, DrawingAction, BoardMembership, ActiveConnection


class WhiteboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.board_id = self.scope['url_route']['kwargs']['board_id']
        self.board_group_name = f'board_{self.board_id}'

        self.user = self.scope["user"]

        if self.user is None or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        if not await self.has_board_access():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name
        )

        await self.accept()

        await self.add_active_connection()

        board_state = await self.get_board_state()
        await self.send(text_data=json.dumps({
            'type': 'board_state',
            'state': board_state
        }))

        await self.broadcast_user_joined()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.board_group_name,
            self.channel_name
        )
        await self.remove_active_connection()
        await self.broadcast_user_left()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'drawing_action':
            await self.handle_drawing_action(data)
        elif message_type == 'cursor_position':
            await self.handle_cursor_position(data)
        elif message_type == 'request_users':
            await self.send_active_users()

    async def handle_drawing_action(self, data):
        # check if a user has edit permission
        if not await self.has_edit_permission():
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'You do not have permission to draw on this board.'
            }))
            return

        # Save the drawing action to the database
        action = await self.save_drawing_action(data)

        # Broadcast the drawing action to all users in the board
        await self.channel_layer.group_send(
            self.board_group_name,
            {
                'type': 'drawing_action',
                'action': action,
                'user': self.user.username
            }
        )

    async def handle_cursor_position(self, data):
        # Broadcast cursor position to others (not saved)
        await self.channel_layer.group_send(
            self.board_group_name,
            {
                'type': 'cursor_position',
                'x': data['x'],
                'y': data['y'],
                'user': self.user.username,
                'channel_name': self.channel_name  # Don't send back to sender
            }
        )

    async def drawing_action(self, event):
        await self.send(text_data=json.dumps({
            'type': 'drawing_action',
            'action': event['action'],
            'user': event['user']
        }))

    async def cursor_position(self, event):
        if event['channel_name'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'cursor_position',
                'x': event['x'],
                'y': event['y'],
                'user': event['user']
            }))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user'],
            'users': event['users']
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user'],
            'users': event['users']
        }))

    async def heartbeat(self, event):
        await self.send(text_data=json.dumps({
            'type': 'heartbeat',
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def has_board_access(self):
        try:
            board = Board.objects.get(id=self.board_id)
            return BoardMembership.objects.filter(board=board, user=self.user).exists()
        except Board.DoesNotExist:
            return False

    @database_sync_to_async
    def has_edit_permission(self):
        try:
            board = Board.objects.get(id=self.board_id)
            membership = BoardMembership.objects.get(board=board, user=self.user)
            return membership.permission in ['edit', 'admin']
        except (Board.DoesNotExist, BoardMembership.DoesNotExist):
            return False

    @database_sync_to_async
    def get_board_state(self):
        try:
            board = Board.objects.get(id=self.board_id)
            return board.get_current_state()
        except Board.DoesNotExist:
            return []

    @database_sync_to_async
    def save_drawing_action(self, data):
        board = Board.objects.get(id=self.board_id)
        action = DrawingAction.objects.create(
            board=board,
            user=self.user,
            action_type=data['action_type'],
            action_data=data['action_data'],
            action_id=data['action_id']
        )
        return {
            'id': action.id,
            'action_type': action.action_type,
            'action_data': action.action_data,
            'action_id': action.action_id,
            'timestamp': str(action.created_at)
        }

    @database_sync_to_async
    def add_active_connection(self):
        board = Board.objects.get(id=self.board_id)
        ActiveConnection.objects.get_or_create(
            board=board,
            user=self.user,
            defaults={
                "channel_name": self.channel_name
            }
        )

    @database_sync_to_async
    def remove_active_connection(self):
        board = Board.objects.get(id=self.board_id)
        ActiveConnection.objects.filter(
            board=board,
            user=self.user,
            channel_name=self.channel_name
        ).delete()

    @database_sync_to_async
    def get_active_users(self):
        board = Board.objects.get(id=self.board_id)
        connections = ActiveConnection.objects.filter(
            board=board
        ).select_related('user')
        return [conn.user.username for conn in connections]

    async def broadcast_user_joined(self):
        users = await self.get_active_users()
        await self.channel_layer.group_send(
            self.board_group_name,
            {
                'type': 'user_joined',
                'user': self.user.username,
                'users': users
            }
        )

    async def broadcast_user_left(self):
        users = await self.get_active_users()
        await self.channel_layer.group_send(
            self.board_group_name,
            {
                'type': 'user_left',
                'user': self.user.username,
                'users': users
            }
        )

    async def send_active_users(self):
        users = await self.get_active_users()
        await self.send(text_data=json.dumps({
            'type': 'active_users',
            'users': users
        }))
