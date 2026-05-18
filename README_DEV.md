# FameShield - Development Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Make (optional, for convenience commands)

### Setup

1. **Clone and navigate to the project:**
```bash
cd fameshield
```

2. **Create environment file:**
```bash
cp backend/.env.example backend/.env
```

3. **Edit `.env` file with your credentials:**
   - Add your Anthropic API key for Claude
   - Add social media API credentials (Twitter, Instagram, TikTok, YouTube)
   - Update database and Redis URLs if needed

4. **Start all services with Docker:**
```bash
make dev
# or
docker-compose up -d
```

5. **Run database migrations:**
```bash
make migrate
# or
cd backend && alembic upgrade head
```

6. **Access the application:**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs
   - Health Check: http://localhost:8000/health

### Development Workflow

#### Starting services
```bash
make dev          # Start all services
make logs         # View logs
make logs-backend # View backend logs only
```

#### Database operations
```bash
make migrate                            # Run migrations
make migrate-create MESSAGE="add users" # Create new migration
make db-shell                           # Open PostgreSQL shell
```

#### Code quality
```bash
make format  # Format code with Black
make lint    # Run flake8 linter
make test    # Run tests
```

#### Stopping services
```bash
make down   # Stop services
make clean  # Stop and remove volumes
```

## Project Structure

```
fameshield/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application entry
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database connection
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── organization.py
│   │   │   ├── user.py
│   │   │   ├── athlete.py
│   │   │   └── social_account.py
│   │   ├── api/               # API endpoints
│   │   │   ├── auth.py        # Authentication
│   │   │   └── athletes.py    # Athlete management
│   │   ├── services/          # Business logic
│   │   │   └── auth_service.py
│   │   ├── adapters/          # Social platform integrations
│   │   │   ├── base_adapter.py
│   │   │   ├── twitter_adapter.py
│   │   │   └── instagram_adapter.py
│   │   ├── workers/           # Celery workers (to be added)
│   │   ├── prompts/           # Claude API prompts (to be added)
│   │   └── templates/         # Report templates (to be added)
│   ├── alembic/               # Database migrations
│   │   └── versions/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── frontend/                  # Next.js frontend (to be added)
├── docs/                      # Documentation
├── docker-compose.yml
├── Makefile
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user and organization
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

### Athletes
- `POST /api/v1/athletes` - Create athlete
- `GET /api/v1/athletes` - List athletes (with filters)
- `GET /api/v1/athletes/{id}` - Get athlete details
- `PATCH /api/v1/athletes/{id}` - Update athlete
- `DELETE /api/v1/athletes/{id}` - Delete athlete
- `GET /api/v1/athletes/{id}/dashboard-stats` - Get athlete stats
- `PATCH /api/v1/athletes/{id}/settings` - Update athlete settings

## Testing the API

### 1. Register a new organization and user
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123",
    "first_name": "John",
    "last_name": "Doe",
    "organization_name": "Elite Athletics"
  }'
```

### 2. Login to get access token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=securepassword123"
```

### 3. Create an athlete (use token from login)
```bash
curl -X POST http://localhost:8000/api/v1/athletes \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah.johnson@example.com",
    "date_of_birth": "2000-05-15",
    "sport": "Swimming",
    "bio": "Olympic swimmer competing at the highest level"
  }'
```

### 4. List athletes
```bash
curl http://localhost:8000/api/v1/athletes \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Next Steps

### Phase 1 (Completed)
✅ Database models and migrations
✅ Authentication with JWT
✅ Athlete management API
✅ Platform adapters (Twitter, Instagram)
✅ Docker development environment

### Phase 2 (To Do)
- [ ] Content monitoring service
- [ ] Claude API classification service
- [ ] Evidence capture service (screenshots)
- [ ] Content and Classification models
- [ ] Celery workers for background tasks
- [ ] Admin dashboard (frontend)

### Phase 3 (To Do)
- [ ] Takedown workflow
- [ ] Escalation rules engine
- [ ] Notification service
- [ ] PDF report generation

### Phase 4 (To Do)
- [ ] Athlete dashboard
- [ ] Analytics and reporting
- [ ] Security audit
- [ ] Beta testing

## Troubleshooting

### Database connection issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Redis connection issues
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Should return: PONG
```

### Backend not starting
```bash
# Check logs
make logs-backend

# Common issues:
# 1. Missing .env file
# 2. Invalid database URL
# 3. Missing dependencies
```

### Running migrations fails
```bash
# Reset database (WARNING: deletes all data)
make clean
make dev
make migrate
```

## Environment Variables

Key environment variables in `backend/.env`:

```bash
# Required for MVP
ANTHROPIC_API_KEY=          # Claude API key (required for classification)
DATABASE_URL=               # PostgreSQL connection string
REDIS_URL=                  # Redis connection string
SECRET_KEY=                 # JWT secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=             # JWT secret (same as above or separate)

# Social Media APIs (optional for Phase 1, required for Phase 2)
TWITTER_BEARER_TOKEN=       # Twitter API v2 Bearer token
INSTAGRAM_APP_ID=           # Instagram/Meta App ID
INSTAGRAM_APP_SECRET=       # Instagram/Meta App Secret
TIKTOK_CLIENT_KEY=          # TikTok API key
YOUTUBE_API_KEY=            # YouTube Data API key

# AWS (required for evidence storage in Phase 2)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `make test`
4. Format code: `make format`
5. Run linter: `make lint`
6. Commit and push
7. Create pull request

## Support

For issues or questions:
- Check the main README.md
- Review API documentation at http://localhost:8000/api/docs
- Check the plan file at `.claude/plans/i-am-working-a-keen-wall.md`
