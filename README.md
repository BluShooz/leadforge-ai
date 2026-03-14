# LeadForge AI

**Autonomous AI-Powered Lead Generation, Outreach, and CRM Platform**

LeadForge AI is a production-ready SaaS platform capable of discovering, qualifying, contacting, and managing 1,000+ business leads per day using artificial intelligence.

## 🚀 Features

### Core Capabilities

- **AI Lead Discovery**: Scrape 1,000+ leads daily from Google Maps, Yelp, LinkedIn, and more
- **AI Lead Scoring**: Automatically score leads 0-100 using Claude/OpenAI
- **CRM Pipeline**: Drag-and-drop Kanban board for lead management
- **AI Outreach Engine**: Generate personalized emails and follow-up sequences
- **Lead Enrichment**: Email validation, website analysis, social media discovery
- **Analytics Dashboard**: Real-time metrics, conversion tracking, and insights
- **Agency Mode**: Audit reports, proposal generation, service recommendations

### Tech Stack

**Frontend**
- Next.js 14 (App Router)
- TypeScript
- TailwindCSS + ShadCN UI
- React Query (TanStack Query)

**Backend**
- FastAPI (Python)
- PostgreSQL
- SQLAlchemy ORM
- Redis (caching & queues)
- Celery (background tasks)

**AI Layer**
- OpenAI GPT-4
- Anthropic Claude
- Custom scoring algorithms

**Scraping Engine**
- Playwright (headless browser)
- BeautifulSoup
- Proxy rotation
- Rate limiting

**Automation**
- n8n (self-hosted)
- Celery Beat (scheduled tasks)

## 📋 Prerequisites

- Docker and Docker Compose
- 4GB RAM minimum (8GB recommended)
- OpenAI or Anthropic API key (optional for full AI features)

## 🔧 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd leadforge-ai

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Configure Environment

Edit `.env` and add at minimum:

```bash
# Required
SECRET_KEY=your-secret-key-here

# For AI features (optional but recommended)
OPENAI_API_KEY=sk-your-openai-key
# OR
ANTHROPIC_API_KEY=sk-ant-your-claude-key

# For email outreach (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
```

### 3. Start All Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- FastAPI Backend (port 8000)
- Next.js Frontend (port 3000)
- Celery Worker
- Celery Beat (scheduler)
- n8n Automation (port 5678)
- Flower (Celery monitoring, port 5555)

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **n8n**: http://localhost:5678 (admin/n8n_password_change_in_production)
- **Flower**: http://localhost:5555

### 5. Create Initial User

```bash
# Via API
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "yourpassword",
    "full_name": "Your Name"
  }'
```

Or register through the web interface at http://localhost:3000/auth/register

## 📊 Usage

### Scraping Leads

**Via API:**
```bash
curl -X POST http://localhost:8000/api/scrape/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "google_maps",
    "search_params": {
      "query": "restaurant",
      "location": "New York, NY"
    }
  }'
```

**Via Dashboard:**
1. Navigate to Dashboard → Scrapers
2. Select source (Google Maps, Yelp)
3. Enter query and location
4. Click "Start Scraping"

### AI Lead Scoring

Leads are automatically scored after scraping:
- **80-100**: Priority leads (high value)
- **50-79**: Good leads
- **0-49**: Low quality

Scoring factors:
- Company size (20 points)
- Industry relevance (20 points)
- Web presence (20 points)
- Location (20 points)
- Growth signals (20 points)

### Email Outreach

1. Navigate to Outreach → Campaigns
2. Create new campaign
3. AI generates email sequence
4. Launch automated outreach

## 🏗️ Project Structure

```
leadforge-ai/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── core/        # Config, security, database
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── workers/     # Celery tasks
│   │   └── main.py      # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/            # Next.js frontend
│   ├── src/
│   │   ├── app/        # Next.js pages
│   │   ├── components/ # React components
│   │   └── lib/        # Utilities, API client
│   ├── Dockerfile
│   └── package.json
├── scrapers/           # Scraping modules
│   ├── google_maps_scraper.py
│   ├── yelp_scraper.py
│   └── base_scraper.py
├── ai-services/        # AI processing
│   ├── scoring.py
│   ├── enrichment.py
│   └── outreach.py
├── docker-compose.yml
└── .env.example
```

## 🔐 Security

**Production Checklist:**

- [ ] Change `SECRET_KEY` in .env
- [ ] Change database password
- [ ] Change Redis password
- [ ] Change n8n admin password
- [ ] Enable HTTPS (reverse proxy)
- [ ] Configure firewall rules
- [ ] Set up API rate limiting
- [ ] Enable request logging
- [ ] Configure backup strategy

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale backend containers
docker-compose up -d --scale backend=3 --scale celery-worker=5
```

### Database Optimization

- Add indexes on frequently queried fields
- Use read replicas for analytics queries
- Archive old leads periodically

### Caching Strategy

Redis caching is enabled for:
- Pipeline statistics
- Analytics summaries
- User sessions
- API rate limits

## 🔄 Database Migrations

```bash
# Create migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Run migration
docker-compose exec backend alembic upgrade head

# Rollback
docker-compose exec backend alembic downgrade -1
```

## 🐛 Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild containers
docker-compose up -d --build
```

### Database connection errors

```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check database is ready
docker-compose exec postgres pg_isready -U leadforge
```

### Scraping not working

```bash
# Check Celery worker logs
docker-compose logs celery-worker

# Check worker is processing tasks
docker-compose exec backend celery -A app.workers.celery_app inspect active
```

## 📚 API Documentation

Full API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Submit pull request

## 📄 License

MIT License - see LICENSE file for details

## 💬 Support

- Documentation: [DEPLOYMENT.md](DEPLOYMENT.md)
- Issues: GitHub Issues
- Email: support@leadforge.ai

## 🔮 Roadmap

- [ ] LinkedIn scraper
- [ ] Multi-language support
- [ ] Mobile app (React Native)
- [ ] White-label CRM
- [ ] Stripe billing integration
- [ ] Advanced analytics
- [ ] AI chatbot integration
- [ ] Voice assistant for calls

---

**Built with ❤️ for sales teams and agencies**
