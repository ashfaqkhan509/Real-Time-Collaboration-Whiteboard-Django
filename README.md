# Real-Time Collaboration Whiteboard (Django)

A real-time collaborative whiteboard built with Django, WebSockets (Django Channels), and a lightweight frontend. This project enables multiple users to draw, add shapes, text, and interact on a shared canvas in real time.

## Features

- Real-time drawing and updates using WebSockets (Django Channels)
- Multiple users can join the same room/canvas
- Basic drawing tools: pen, line, rectangle, circle, text
- Clear canvas and undo/redo support (if implemented)
- Room management (create/join rooms)

## Tech stack

- Backend: Django
- Real-time: Django Channels (ASGI)
- Frontend: HTML/CSS/JavaScript (Canvas API)
- Optional: Redis as Channels layer backend for production

## Requirements

- Python 3.8+
- Django 3.2+ (or newer)
- channels
- channels_redis (if using Redis)

Install dependencies (recommend using a virtual environment):

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

If you don't have a requirements file, install core packages:

```bash
pip install django channels
# For Redis channel layer
pip install channels_redis
```

## Configuration

1. Set up Django project settings as needed (SECRET_KEY, ALLOWED_HOSTS, DEBUG).
2. If using Redis for Channels, configure CHANNEL_LAYERS in settings.py:

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

3. Apply migrations:

```bash
python manage.py migrate
```

## Running locally

Run the development server (ASGI):

```bash
# If using Daphne (recommended for Channels)
pip install daphne
daphne -b 0.0.0.0 -p 8000 your_project_name.asgi:application

# Or use the runserver command for quick testing
python manage.py runserver
```

Open your browser at http://127.0.0.1:8000 and create or join a whiteboard room.

## Usage

- Create a room or open an existing room URL in multiple browser tabs.
- Use drawing tools on the canvas; updates are broadcast to all participants in the room.

## Testing

- Add tests under the app's `tests.py` or `tests/` directory and run:

```bash
python manage.py test
```

## Deployment notes

- Use Daphne or an ASGI-compatible server in production.
- Configure Redis as the channel layer for scaling across multiple processes/hosts.
- Use HTTPS and proper security settings (allowed hosts, secure cookies).

## Contributing

Contributions are welcome. Open an issue or submit a pull request with a clear description of changes.

## License

Add a LICENSE file to declare the project's license. If you have no preference yet, consider MIT.

---

If you'd like, I can also:
- Add a requirements.txt based on the project's imports
- Create setup and run scripts (docker-compose) for local development
- Add a sample .env.example and configuration docs

Tell me which you'd like next and I'll update the repo.