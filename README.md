# FastAPI + OpenAI Realtime API Voice Chat Application

A modern web application built with FastAPI, PostgreSQL, Redis, Celery, and OpenAI's Realtime API for voice-to-voice conversations.

## 🚀 Features

- **Voice-to-Voice Chat**: Real-time voice conversations using OpenAI's Realtime API
- **Text Chat**: Traditional text-based chat functionality
- **WebSocket Support**: Real-time communication with WebSocket connections
- **User Authentication**: JWT-based authentication system
- **Database Integration**: PostgreSQL with SQLAlchemy ORM
- **Background Tasks**: Celery for asynchronous task processing
- **Daily Data Fetching**: Automated daily tasks to fetch data from websites
- **Redis Caching**: Fast data caching and session management
- **Docker Support**: Fully containerized application

## 🏗️ Architecture

```
├── FastAPI Backend
│   ├── Authentication (JWT)
│   ├── Chat API (Text & Voice)
│   ├── WebSocket Manager
│   └── Voice Chat Manager (OpenAI Realtime API)
├── PostgreSQL Database
├── Redis (Caching & Celery Broker)
├── Celery Workers
│   ├── Background Tasks
│   └── Daily Data Fetching
└── Frontend (HTML/JS)
    ├── Text Chat Interface
    └── Voice Chat Interface
```

## 📋 Prerequisites

- Docker and Docker Compose
- OpenAI API Key
- Python 3.11+ (for local development)

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd 12062025
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
DATABASE_URL=postgresql+asyncpg://username:password@db/postgresdb
SYNC_DATABASE_URL=postgresql+psycopg2://username:password@db/postgresdb
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. Get OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API Keys section
4. Create a new API key
5. Add the key to your `.env` file

### 4. Start the Application

```bash
docker-compose up --build
```

This will start all services:
- **FastAPI App**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled task execution

## 🎯 Usage

### Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Text Chat Demo**: http://localhost:8000/chat/demo
- **Voice Chat Demo**: http://localhost:8000/chat/voice-demo
- **Health Check**: http://localhost:8000/health

### Voice Chat Features

1. **Real-time Voice Conversation**:
   - Click the microphone button to start recording
   - Speak naturally to the AI assistant
   - Receive voice responses in real-time

2. **Text Input**:
   - Type messages in the text input field
   - AI will respond with both text and voice

3. **Audio Features**:
   - Speech-to-text transcription
   - Text-to-speech synthesis
   - Real-time audio streaming

### API Endpoints

#### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info

#### Chat
- `GET /chat/rooms` - List chat rooms
- `POST /chat/rooms` - Create chat room
- `GET /chat/rooms/{room_id}` - Get room details
- `POST /chat/rooms/{room_id}/join` - Join chat room
- `WS /chat/ws/{room_id}` - WebSocket for text chat
- `WS /chat/voice/{room_id}` - WebSocket for voice chat

#### Tasks
- `POST /tasks/run` - Run background task
- `GET /tasks/status/{task_id}` - Check task status

## 🔧 Development

### Local Development Setup

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Database Migration**:
```bash
alembic upgrade head
```

3. **Run FastAPI**:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. **Run Celery Worker**:
```bash
celery -A celery_app worker --loglevel=info
```

5. **Run Celery Beat**:
```bash
celery -A celery_app beat --loglevel=info
```

### Project Structure

```
src/
├── auth/                 # Authentication module
│   ├── api.py           # Auth endpoints
│   ├── models.py        # User models
│   └── schema.py        # Auth schemas
├── chat/                # Chat module
│   ├── api.py           # Chat endpoints
│   ├── models.py        # Chat models
│   ├── schema.py        # Chat schemas
│   ├── websocket_manager.py  # WebSocket management
│   ├── voice_chat.py    # Voice chat with OpenAI
│   └── templates/       # HTML templates
│       ├── chat.html    # Text chat interface
│       └── voice_chat.html  # Voice chat interface
├── tasks/               # Background tasks
│   ├── tasks.py         # General tasks
│   └── daily_fetch.py   # Daily data fetching
├── alembic/             # Database migrations
├── config.py            # Configuration settings
├── database.py          # Database setup
├── main.py              # FastAPI application
├── celery_app.py        # Celery configuration
├── celery_tasks.py      # Celery task definitions
└── redis_client.py      # Redis client setup
```

## 🔄 Background Tasks

### Daily Data Fetching

The application includes a daily task that fetches data from websites and saves it to the database:

- **Schedule**: Runs every 24 hours
- **Default URLs**: 
  - JSONPlaceholder API
  - HTTPBin JSON endpoint
  - GitHub API
- **Storage**: Data is saved to `daily_fetched_data` table
- **Caching**: Results are cached in Redis

### Custom Tasks

You can add custom background tasks by:

1. Creating task functions in `src/tasks/`
2. Registering them in `celery_tasks.py`
3. Adding to beat schedule in `celery_app.py`

## 🐳 Docker Services

### Services Overview

- **web**: FastAPI application
- **db**: PostgreSQL database
- **redis**: Redis cache and message broker
- **celery**: Celery worker for background tasks
- **celery-beat**: Celery beat scheduler

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f celery

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build

# Run database migrations
docker-compose exec web alembic upgrade head
```

## 🔍 Monitoring & Debugging

### Health Checks

- **Application Health**: `GET /health`
- **Database Health**: Included in health endpoint
- **Redis Health**: Included in health endpoint

### Logs

```bash
# Application logs
docker-compose logs -f web

# Celery worker logs
docker-compose logs -f celery

# Database logs
docker-compose logs -f db
```

### Common Issues

1. **OpenAI API Key Issues**:
   - Ensure your API key is valid
   - Check if you have sufficient credits
   - Verify the key is correctly set in `.env`

2. **WebSocket Connection Issues**:
   - Check if ports are properly exposed
   - Verify firewall settings
   - Ensure WebSocket endpoint is accessible

3. **Database Connection Issues**:
   - Wait for PostgreSQL to fully start
   - Check database credentials in `.env`
   - Run migrations: `alembic upgrade head`

## 🚀 Deployment

### Production Deployment

1. **Environment Variables**:
   - Set strong `SECRET_KEY`
   - Use production database URLs
   - Configure proper Redis URLs
   - Set valid OpenAI API key

2. **Security**:
   - Use HTTPS in production
   - Set proper CORS origins
   - Configure firewall rules
   - Use environment-specific secrets

3. **Scaling**:
   - Use multiple Celery workers
   - Implement load balancing
   - Use managed database services
   - Configure Redis clustering

## 📝 API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Create an issue in the repository

---

**Built with ❤️ using FastAPI, OpenAI Realtime API, and modern web technologies.**
