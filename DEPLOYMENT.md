# LeadForge AI - Deployment Guide

This guide covers deploying LeadForge AI to production using Docker Compose, Railway, Render, or Vercel.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Deployment Options](#deployment-options)
4. [Database Setup](#database-setup)
5. [Monitoring & Logging](#monitoring--logging)
6. [Security Hardening](#security-hardening)
7. [Backup Strategy](#backup-strategy)
8. [Scaling Guidelines](#scaling-guidelines)

---

## Prerequisites

### Required

- Docker & Docker Compose
- Domain name
- SSL certificate (Let's Encrypt recommended)

### API Keys

- OpenAI API Key (https://platform.openai.com/api-keys)
- Anthropic API Key (https://console.anthropic.com/settings/keys) - alternative to OpenAI
- NeverBounce API Key (https://app.neverbounce.com/account/api) - optional

### For Email Outreach

- SendGrid API Key (https://app.sendgrid.com/settings/api_keys)
- Or SMTP credentials

---

## Environment Configuration

### Production .env

```bash
# =============================================================================
# REQUIRED - Change these in production
# =============================================================================
SECRET_KEY=$(openssl rand -hex 32)  # Generate new secret key

# Database (use strong password)
DATABASE_URL=postgresql://leadforge:STRONG_PASSWORD_HERE@postgres:5432/leadforge

# Redis (use strong password)
REDIS_URL=redis://:REDIS_PASSWORD_HERE@redis:6379/0

# =============================================================================
# API KEYS
# =============================================================================
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-claude-key
NEVERBOUNCE_API_KEY=your-neverbounce-key

# =============================================================================
# EMAIL (for outreach)
# =============================================================================
SENDGRID_API_KEY=SG.your-sendgrid-key
# OR SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# =============================================================================
# SECURITY
# =============================================================================
ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://your-domain.com
BACKEND_URL=https://api.your-domain.com

# =============================================================================
# STRIPE (future billing)
# =============================================================================
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# =============================================================================
# PROXIES (for scraping)
# =============================================================================
PROXY_ROTATION_ENABLED=true
PROXY_SERVICE_URL=https://proxy-service.com
PROXY_SERVICE_USERNAME=your-username
PROXY_SERVICE_PASSWORD=your-password
```

---

## Deployment Options

### Option 1: Self-Hosted (Docker Compose)

**Best for:** Full control, cost-effective, single-tenant

#### 1.1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone <your-repo-url>
cd leadforge-ai

# Configure environment
cp .env.example .env
nano .env  # Edit with production values
```

#### 1.2. Deploy with SSL (Caddy)

Create `Caddyfile`:

```caddyfile
your-domain.com {
    reverse_proxy frontend:3000
}

api.your-domain.com {
    reverse_proxy backend:8000
}

n8n.your-domain.com {
    reverse_proxy n8n:5678
}
```

Update `docker-compose.yml` to add Caddy:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - leadforge-network

volumes:
  caddy_data:
  caddy_config:
```

#### 1.3. Start Services

```bash
# Build and start
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

### Option 2: Railway (Backend + Database)

**Best for:** Easy deployment, auto-scaling, managed infrastructure

#### 2.1. Deploy Backend

1. Create Railway account
2. Create new project
3. Deploy from GitHub
4. Configure environment variables
5. Railway will automatically:
   - Build Docker container
   - Host PostgreSQL database
   - Provide Redis instance
   - Assign domain

#### 2.2. Environment Variables in Railway

Set these in Railway dashboard:
- `DATABASE_URL` (auto-provided)
- `REDIS_URL` (auto-provided)
- `SECRET_KEY` (generate new)
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- All other .env values

#### 2.3. Deploy Frontend Separately

Use Vercel for frontend (see Option 3)

---

### Option 3: Vercel (Frontend Only)

**Best for:** Frontend hosting, CDN, automatic deployments

#### 3.1. Install Vercel CLI

```bash
npm install -g vercel
```

#### 3.2. Deploy

```bash
cd frontend
vercel

# Set environment variable in Vercel dashboard:
# NEXT_PUBLIC_API_URL=https://your-railway-backend-url.railway.app
```

#### 3.3. Custom Domain

1. Add domain in Vercel dashboard
2. Update DNS records
3. Vercel auto-configures SSL

---

### Option 4: Render (Full Stack)

**Best for:** Simple deployment, free tier available

#### 4.1. Backend + Database

1. Connect GitHub repo to Render
2. Create "Web Service" for backend
3. Create "PostgreSQL" database
4. Create "Redis" instance
5. Add environment variables

#### 4.2. Frontend

1. Create another "Web Service" for frontend
2. Set build command: `npm run build`
3. Set start command: `npm start`
4. Add `NEXT_PUBLIC_API_URL` environment variable

---

## Database Setup

### Initial Migrations

```bash
# Run Alembic migrations
docker-compose exec backend alembic upgrade head

# Initialize default pipeline stages
# Via API or admin panel
```

### Database Backups

```bash
# Manual backup
docker-compose exec postgres pg_dump -U leadforge leadforge > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U leadforge leadforge < backup.sql

# Automated backup script
```

Create `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U leadforge leadforge > "$BACKUP_DIR/backup_$DATE.sql"
# Keep last 7 days
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/scripts/backup.sh
```

---

## Monitoring & Logging

### Application Logs

```bash
# View all logs
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Flower (Celery Monitoring)

Access at http://your-server:5555

Monitor:
- Active tasks
- Task history
- Worker status
- Task success/failure rates

### Prometheus Metrics (Optional)

Add to `backend/app/main.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('http_requests_total', 'Total requests')
request_duration = Histogram('http_request_duration_seconds', 'Request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## Security Hardening

### 1. Change Default Passwords

```bash
# Generate strong passwords
openssl rand -base64 32
```

Update in `.env`:
- Database password
- Redis password
- n8n admin password

### 2. Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 3. Rate Limiting

Already configured in `backend/app/core/rate_limit.py`

Adjust limits per endpoint:
```python
rate_limit_api = RateLimiter(requests=100, window=60)
```

### 4. CORS Configuration

Update in `.env`:
```bash
FRONTEND_URL=https://your-domain.com
ALLOWED_ORIGINS=["https://your-domain.com"]
```

### 5. Security Headers

Add to `backend/app/main.py`:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# Redirect HTTP to HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts only
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["your-domain.com", "api.your-domain.com"]
)
```

---

## Backup Strategy

### Backup Checklist

- [ ] Database backups (daily)
- [ ] Redis backups (hourly for queue state)
- [ ] File storage backups (if any)
- [ ] Environment variables backup
- [ ] Code repository backup

### Backup Locations

- **Local**: Server directory
- **Remote**: AWS S3, Google Cloud Storage, or Backblaze B2
- **Offsite**: Different geographical region

### Recovery Testing

**Test monthly:**

```bash
# Restore to test environment
docker-compose -f docker-compose.test.yml up -d
docker-compose exec -T postgres psql -U leadforge leadforge_test < backup.sql
# Verify data integrity
```

---

## Scaling Guidelines

### Vertical Scaling (More Power)

**When to use:** < 5,000 leads per day

**Server specs:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB SSD

**Docker Compose:**
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### Horizontal Scaling (More Servers)

**When to use:** > 5,000 leads per day

#### Load Balancer (Nginx)

```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

#### Multiple Workers

```bash
# Scale Celery workers
docker-compose up -d --scale celery-worker=5
```

#### Database Read Replicas

For analytics queries:
```python
# Add read replica in config
SQLALCHEMY_DATABASE_URI = 'postgresql://...'
SQLALCHEMY_REPLICAS = {
    'read_only': 'postgresql://replica-host...'
}
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs backend

# Rebuild without cache
docker-compose build --no-cache backend
docker-compose up -d
```

### Database connection errors

```bash
# Check database is ready
docker-compose exec postgres pg_isready -U leadforge

# Restart database
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### High memory usage

```bash
# Check container stats
docker stats

# Limit container memory
# In docker-compose.yml:
services:
  backend:
    mem_limit: 2g
```

### Scraping not working

```bash
# Check Celery worker
docker-compose logs celery-worker

# Check scheduled tasks
docker-compose logs celery-beat

# Inspect active tasks
docker-compose exec backend celery -A app.workers.celery_app inspect active
```

---

## Performance Optimization

### Database Indexes

```sql
-- Add indexes for common queries
CREATE INDEX idx_leads_org_score ON leads(organization_id, lead_score);
CREATE INDEX idx_leads_status ON leads(status) WHERE status != 'lost';
CREATE INDEX idx_leads_search ON leads USING gin(to_tsvector('english', business_name || ' ' || contact_name));
```

### Redis Caching

Already enabled for:
- Pipeline stats
- Analytics summaries
- User sessions

Cache duration: 5 minutes

### CDN Configuration

Use CDN for:
- Frontend static assets
- Email templates
- Public images

---

## Cost Estimates

### Self-Hosted (Monthly)

- Server (4GB RAM): $20-40
- Domain: $10-15/year
- SSL: Free (Let's Encrypt)
- Proxies (optional): $50-200
- **Total**: $20-200/month

### Cloud-Hosted (Monthly)

- Railway (backend + DB): $20-100
- Vercel (frontend): Free - $20
- SendGrid (email): $15-100
- OpenAI API: $10-100
- **Total**: $50-300/month

---

## Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Review troubleshooting section
3. GitHub Issues
4. Email: support@leadforge.ai

---

**Last updated:** 2026-03-13
