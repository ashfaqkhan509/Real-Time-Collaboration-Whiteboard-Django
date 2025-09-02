import pytest
import json
import asyncio
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
import async_timeout
from whiteboard_app.models import Board, BoardMembership, DrawingAction
from whiteboard_app.consumers import WhiteboardConsumer


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestWhiteboardConsumer:
    """Integration tests for WhiteboardConsumer WebSocket functionality"""
    
    async def create_user(self, username, password="testpass123"):
        """Create a test user"""
        user = await sync_to_async(User.objects.create_user)(
            username=username,
            password=password
        )
        return user
    
    async def create_board(self, name, user):
        """Create a test board with a user as admin"""
        board = await sync_to_async(Board.objects.create)(
            name=name,
            created_by=user
        )
        await sync_to_async(BoardMembership.objects.create)(
            board=board,
            user=user,
            permission='admin'
        )
        return board
    
    async def add_user_to_board(self, user, board, permission='view'):
        """Add a user to a board with specified permission"""
        membership = await sync_to_async(BoardMembership.objects.create)(
            board=board,
            user=user,
            permission=permission
        )
        return membership
    
    async def test_websocket_connection_authenticated(self):
        """Test WebSocket connection with authenticated user"""
        # Create user and board
        user = await self.create_user("testuser")
        board = await self.create_board("Test Board", user)
        
        # Create communicator with authenticated user
        communicator = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }
        
        # Connect to WebSocket
        connected, _ = await communicator.connect()
        assert connected
        
        # Check that initial board state is sent
        response = await communicator.receive_json_from()
        assert response['type'] == 'board_state'
        assert 'state' in response
        
        # Check that user joined message is sent
        response = await communicator.receive_json_from()
        assert response['type'] == 'user_joined'
        assert response['user'] == 'testuser'
        
        # Disconnect
        await communicator.disconnect()
    
    async def test_websocket_connection_unauthenticated(self):
        """Test WebSocket connection with unauthenticated user"""

        user = await self.create_user("testuser")
        board = await self.create_board("Test Board", user)
        
        # Create communicator without authenticated user
        communicator = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator.scope['user'] = None
        communicator.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }

        connected, code = await communicator.connect()
        assert not connected
        assert code == 4401
    
    async def test_websocket_connection_no_board_access(self):
        """Test WebSocket connection with user who doesn't have board access"""

        user1 = await self.create_user("user1")
        user2 = await self.create_user("user2")
        board = await self.create_board("Test Board", user1)
        
        # Create communicator with user2 (no access to board)
        communicator = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator.scope['user'] = user2
        communicator.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }

        connected, code = await communicator.connect()
        assert not connected
        assert code == 4403  # Forbidden
    
    async def test_multiple_users_in_same_group(self):
        """Test multiple users connecting to the same board group"""
        # Create users and board
        user1 = await self.create_user("user1")
        user2 = await self.create_user("user2")
        board = await self.create_board("Test Board", user1)
        await self.add_user_to_board(user2, board, 'edit')
        
        # Create communicators for both users
        communicator1 = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator1.scope['user'] = user1
        communicator1.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }
        
        communicator2 = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator2.scope['user'] = user2
        communicator2.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }
        
        # Connect both users
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        assert connected1
        assert connected2
        
        # User1 should receive board state and user joined message for themselves
        response1 = await communicator1.receive_json_from()
        assert response1['type'] == 'board_state'
        
        response1 = await communicator1.receive_json_from()
        assert response1['type'] == 'user_joined'
        assert response1['user'] == 'user1'
        
        # User2 should receive user joined message for user1 when they connect
        response2 = await communicator2.receive_json_from()
        assert response2['type'] == 'board_state'
        
        response2 = await communicator2.receive_json_from()
        assert response2['type'] == 'user_joined'
        assert response2['user'] == 'user1'
        
        # User1 should receive user joined message for user2
        response1 = await communicator1.receive_json_from()
        assert response1['type'] == 'user_joined'
        assert response1['user'] == 'user2'
        
        # Disconnect both users
        await communicator1.disconnect()
        await communicator2.disconnect()
    
    async def test_drawing_action_persistence(self):
        """Test that drawing actions are persisted to database"""
        # Create user and board
        user = await self.create_user("testuser")
        board = await self.create_board("Test Board", user)
        
        # Create communicator
        communicator = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }
        
        # Connect to WebSocket
        connected, _ = await communicator.connect()
        assert connected
        
        # Skip initial messages
        await communicator.receive_json_from()  # board_state
        await communicator.receive_json_from()  # user_joined
        
        # Send a drawing action
        drawing_data = {
            "type": "drawing_action",
            "action_type": "draw",
            "action_data": {
                "points": [{"x": 10, "y": 20}, {"x": 30, "y": 40}],
                "color": "#ff0000",
                "lineWidth": 3
            },
            "action_id": "test_action_123"
        }
        await communicator.send_json_to(drawing_data)
        
        # Wait a bit for the action to be processed
        await communicator.wait()
        
        # Check that the action was saved to database
        actions = await sync_to_async(list)(DrawingAction.objects.filter(board=board))
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "draw"
        # Use sync_to_async to access the user relationship
        action_user = await sync_to_async(lambda: action.user)()
        assert action_user == user
        assert action.action_data == drawing_data["action_data"]
        
        # Disconnect
        try:
            await communicator.disconnect()
        except asyncio.CancelledError:
            pass
    
    async def test_drawing_action_broadcast(self):
        """Test that drawing actions are broadcast to all users in the group"""
        # Create users and board
        user1 = await self.create_user("user1")
        user2 = await self.create_user("user2")
        board = await self.create_board("Test Board", user1)
        await self.add_user_to_board(user2, board, 'edit')
        
        # Create communicators for both users
        communicator1 = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator1.scope['user'] = user1
        communicator1.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }
        
        communicator2 = WebsocketCommunicator(
            WhiteboardConsumer.as_asgi(),
            f"/ws/board/{board.id}/"
        )
        communicator2.scope['user'] = user2
        communicator2.scope['url_route'] = {
            'kwargs': {
                'board_id': board.id
            }
        }
        
        # Connect both users
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        assert connected1
        assert connected2
        
        # Skip initial messages
        await communicator1.receive_json_from()  # board_state
        await communicator1.receive_json_from()  # user_joined
        await communicator2.receive_json_from()  # board_state
        await communicator2.receive_json_from()  # user_joined
        await communicator1.receive_json_from()  # user_joined (user2)
        
        # User1 sends a drawing action
        drawing_data = {
            "type": "drawing_action",
            "action_type": "draw",
            "action_data": {
                "points": [{"x": 10, "y": 20}, {"x": 30, "y": 40}],
                "color": "#ff0000",
                "lineWidth": 3
            },
            "action_id": "test_action_123"
        }
        await communicator1.send_json_to(drawing_data)
        
        # User2 should receive the drawing action
        # Try to receive messages with a longer timeout
        drawing_action_received_by_user2 = False
        try:
            async with async_timeout.timeout(2):
                while not drawing_action_received_by_user2:
                    msg = await communicator2.receive_json_from(timeout=0.5)
                    print(f"User2 received message: {msg}")
                    if msg['type'] == 'drawing_action':
                        assert msg['action']['action_type'] == 'draw'
                        assert msg['user'] == 'user1'
                        drawing_action_received_by_user2 = True
        except asyncio.TimeoutError:
            pass
        
        # User1 should also receive the drawing action (broadcast to all including sender)
        drawing_action_received_by_user1 = False
        try:
            async with async_timeout.timeout(2):
                while not drawing_action_received_by_user1:
                    msg = await communicator1.receive_json_from(timeout=0.5)
                    print(f"User1 received message: {msg}")
                    if msg['type'] == 'drawing_action':
                        assert msg['action']['action_type'] == 'draw'
                        assert msg['user'] == 'user1'
                        drawing_action_received_by_user1 = True
        except asyncio.TimeoutError:
            pass
        
        assert drawing_action_received_by_user2, "User2 did not receive the drawing action"
        assert drawing_action_received_by_user1, "User1 did not receive the drawing action"
        
        # Disconnect both users
        await communicator1.disconnect()
        await communicator2.disconnect()
