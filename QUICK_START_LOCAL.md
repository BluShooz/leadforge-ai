# LeadForge AI - Quick Start (Local, No Docker)

## Prerequisites
- Python 3.11+
- Node.js 20+
- npm or yarn

## Backend Setup

### 1. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Create Local Database
```bash
# Using SQLite for local development (simpler than PostgreSQL)
export DATABASE_URL=sqlite:///./leadforge.db
```

### 3. Run Backend
```bash
# Terminal 1: Run FastAPI server
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Run Celery worker (optional, for background tasks)
celery -A app.workers.celery_app worker --loglevel=info
```

Backend will be available at: http://localhost:8000

## Frontend Setup

### 1. Install Node Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment
Create `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Frontend
```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:3000

## Testing

1. Open http://localhost:3000
2. Register a new account
3. Access API docs at http://localhost:8000/docs

## Notes
- SQLite will be used instead of PostgreSQL
- Redis features will be optional
- Scrapers will work with rate limiting
- AI features will use rule-based scoring if no API key provided
