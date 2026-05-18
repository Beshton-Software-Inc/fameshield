# FameShield - AI Athlete Protection Platform

**Protect athletes from AI disinformation and social media bullying with AI-powered monitoring and response.**

---

## Overview

FameShield is a B2B SaaS platform that helps sports organizations, federations, schools, and agencies protect their athletes from:

1. **AI disinformation / impersonation** - Fake stories, quotes, images, videos, and endorsements
2. **Social media bullying** - Harassment, racism, sexism, threats, doxxing, body-shaming
3. **Mental health harm** - Psychological impact of online abuse
4. **Weak response workflows** - Lack of evidence packaging and takedown processes

### Key Differentiator

Most tools stop at content moderation. **FameShield goes further:**

```
Detect → Classify → Preserve Evidence → Recommend Action → Route to Human Support
```

---

## MVP Features (Phase 1 Complete)

✅ **1. Athlete Profile Monitoring**
- Track mentions and comments across Twitter, Instagram, TikTok, YouTube
- Real-time content ingestion with deduplication

✅ **2. User Authentication & Authorization**
- JWT-based authentication with refresh tokens
- Role-based access control (Admin, Coach, Agent, Legal, etc.)
- Multi-tenant organization management

✅ **3. Platform Adapters**
- Twitter/X API v2 integration
- Instagram Graph API integration
- Extensible adapter pattern for additional platforms

✅ **4. Database Models**
- Organizations, Users, Athletes, Social Accounts
- PostgreSQL with async SQLAlchemy
- Alembic migrations

✅ **5. RESTful API**
- FastAPI with automatic OpenAPI documentation
- Async endpoints for high performance
- Comprehensive error handling

✅ **6. Development Environment**
- Docker Compose for local development
- PostgreSQL + Redis + FastAPI + Celery
- Hot-reload for rapid development

---

## Coming in Phase 2

🚧 **Content Classification (Claude API)**
- 12-category abuse detection (harassment, hate speech, threats, etc.)
- 5-level severity scoring (1=log only → 5=immediate escalation)
- Context-aware analysis (athlete demographics, recent events)

🚧 **Evidence Capture Vault**
- Automated screenshot capture with Playwright
- Metadata preservation (timestamps, author info, engagement)
- S3 storage with chain of custody tracking
- SHA-256 checksums for integrity

🚧 **Monitoring Service**
- Celery workers for background processing
- Scheduled polling of social platforms
- Rate limiting and intelligent queuing

🚧 **Admin Dashboard (Frontend)**
- Real-time classification feed
- Filterable content view
- Evidence viewer
- Manual review interface

---

## Technology Stack

**Backend:**
- **Framework:** Python 3.11 + FastAPI
- **Database:** PostgreSQL 15 + TimescaleDB
- **Cache/Queue:** Redis
- **Task Queue:** Celery
- **AI:** Anthropic Claude API
- **Cloud:** AWS (S3, Rekognition)

**Frontend (To Be Built):**
- **Framework:** Next.js 14+ (React)
- **UI:** Shadcn/ui + Tailwind CSS
- **State:** React Query + Zustand
- **Charts:** Recharts

**Infrastructure:**
- **Containerization:** Docker + Docker Compose
- **IaC:** Terraform (planned)
- **CI/CD:** GitHub Actions (planned)

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Make (optional)

### 1. Clone and setup
```bash
cd fameshield
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

### 2. Start services
```bash
make dev
# or: docker-compose up -d
```

### 3. Run migrations
```bash
make migrate
# or: cd backend && alembic upgrade head
```

### 4. Access the API
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/api/docs
- **Health:** http://localhost:8000/health

See **[README_DEV.md](README_DEV.md)** for detailed development instructions.

---

## Project Structure

```
fameshield/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── main.py        # Application entry point
│   │   ├── config.py      # Settings management
│   │   ├── database.py    # Database connection
│   │   ├── models/        # SQLAlchemy models
│   │   ├── api/           # API endpoints
│   │   ├── services/      # Business logic
│   │   ├── adapters/      # Social platform integrations
│   │   ├── workers/       # Celery workers (Phase 2)
│   │   ├── prompts/       # Claude prompts (Phase 2)
│   │   └── templates/     # Report templates (Phase 3)
│   ├── alembic/           # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              # Next.js frontend (Phase 2+)
├── docs/                  # Documentation
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## API Examples

### Register Organization & User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@athletics.com",
    "password": "securepass123",
    "first_name": "Jane",
    "last_name": "Smith",
    "organization_name": "Elite Sports Academy"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@athletics.com&password=securepass123"
```

### Create Athlete
```bash
curl -X POST http://localhost:8000/api/v1/athletes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Emma",
    "last_name": "Wilson",
    "email": "emma.wilson@example.com",
    "date_of_birth": "2002-08-20",
    "sport": "Track and Field"
  }'
```

See full API documentation at http://localhost:8000/api/docs

---

## Roadmap

### ✅ Phase 1: Foundation (Weeks 1-4) - COMPLETE
- Database models and migrations
- Authentication with JWT and RBAC
- Athlete management API
- Platform adapters (Twitter, Instagram)
- Docker development environment

### 🚧 Phase 2: Monitoring & Classification (Weeks 5-8) - IN PROGRESS
- Monitoring service with Celery workers
- Claude API classification (12 categories, 5 severity levels)
- Evidence capture service (screenshots, metadata)
- Content and Classification models
- Admin dashboard (basic)

### 📅 Phase 3: Workflow & Automation (Weeks 9-12)
- Takedown request workflow
- PDF report generation
- Escalation rules engine
- Notification service (email, SMS, real-time)
- Platform API integration for submissions

### 📅 Phase 4: Polish & Launch (Weeks 13-16)
- Athlete-facing dashboard
- Analytics and reporting
- Organization settings
- Security audit
- Beta testing with pilot customers

---

## Target Customers

**Best first target:** Female athletes, youth elite athletes, Olympic-style sports

**Customer types:**
- Sports federations (Olympics, NCAA, etc.)
- High schools and clubs
- Colleges and universities
- Athlete agencies
- Women's sports leagues
- NIL collectives

**Pricing tiers:**
- Individual athlete: $20–100/month
- Agency: $500–5,000/month
- School/team: $1,000–10,000/month
- Federation/league: Enterprise contracts

---

## Detection Categories

The AI classifies content into **12 categories**:

1. **Normal criticism** - Legitimate sports commentary
2. **Harassment** - Targeted personal attacks
3. **Hate speech** - Racist, sexist, discriminatory content
4. **Sexual harassment** - Unwanted sexual comments
5. **Threat of violence** - Explicit or implied threats
6. **Doxxing** - Sharing private information
7. **Impersonation** - Fake accounts pretending to be the athlete
8. **Fake quote** - Falsely attributed statements
9. **Fake endorsement** - False product/brand association
10. **Deepfake** - AI-generated or manipulated media
11. **Coordinated attack** - Organized harassment campaign
12. **Gambling-related abuse** - Betting-related harassment

---

## Severity Levels

**Level 1:** Negative fan comment → Log only  
**Level 2:** Bullying/personal attack → Flag for review  
**Level 3:** Hate speech/sexual harassment → Hide from athlete, notify admin  
**Level 4:** Doxxing/credible threat → **Immediate human review**  
**Level 5:** Coordinated attack/criminal threat → **Urgent escalation to law enforcement**

---

## Security & Privacy

- **Authentication:** JWT with short expiration (15 min access, 7 day refresh)
- **Authorization:** Role-based access control (RBAC) with fine-grained permissions
- **Encryption:** AES-256 at rest, TLS 1.3 in transit
- **Compliance:** GDPR, COPPA, FERPA (for schools), SOC 2 Type II (planned)
- **Data Retention:** Evidence 7 years, content metadata 2 years
- **Privacy:** Athlete consent required, opt-out available

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Format code: `make format`
6. Submit a pull request

---

## License

Copyright © 2026 FameShield. All rights reserved.

---

## Support & Documentation

- **Development Guide:** [README_DEV.md](README_DEV.md)
- **API Docs:** http://localhost:8000/api/docs
- **Implementation Plan:** `.claude/plans/i-am-working-a-keen-wall.md`
- **Product Vision:** See original README.md

---

## Acknowledgments

Built with Claude Code by Anthropic.

Inspired by real-world programs:
- IOC's AI monitoring for Paris 2024 Olympics
- FIFA's Social Media Protection Service
- NCAA's athlete safety initiatives

**Protecting athletes. Powered by AI.**
