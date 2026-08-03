from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Board
from datetime import datetime


@shared_task
def send_heartbeat():
    """
    Send heartbeat messages to all connected users on all boards
    """
    channel_layer = get_channel_layer()

    # Get all boards
    boards = Board.objects.all()

    # Send heartbeat to each board group
    for board in boards:
        board_group_name = f'board_{board.id}'

        # Send heartbeat message to the board group
        async_to_sync(channel_layer.group_send)(
            board_group_name,
            {
                'type': 'heartbeat',
                'timestamp': datetime.now().isoformat()
            }
        )


@shared_task
def create_board_snapshot():
    """
    Create snapshots for all boards
    """
    from .models import Board  # noqa: E402

    for board in Board.objects.all():
        try:
            state = board.get_current_state()
            board.snapshots.create(snapshot_data=state)
            print(f"Snapshot created for board {board.name}")
        except Exception as e:
            print(f"Failed to create snapshot for {board.id}: {e}")

    return "All board snapshots created"
