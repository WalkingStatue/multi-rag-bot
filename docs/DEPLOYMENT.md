# Deployment Guide

This guide covers deploying the Multi-Bot RAG Platform to various environments including production, staging, and cloud platforms.

## 🚀 Production Deployment

### Prerequisites

- **Docker & Docker Compose**
- **Domain name** (for HTTPS)
- **SSL Certificate** (Let's Encrypt recommended)
- **Minimum 4GB RAM, 2 CPU cores**
- **50GB+ storage** (for documents and vector data)

### Quick Production Setup

1. **Clone and configure**
   ```bash
   git clone <your-repository-url>
   cd multi-bot-rag-platform
   cp config/.env.example config/.env
   ```

2. **Update production environment**
   ```bash
   # Edit config/.env
   NODE_ENV=production
   SECRET_KEY=<generate-strong-32-char-key>
   DATABASE_URL=postgresql://user:pass@localhost:5432/prod_db
   FRONTEND_URL=https://yourdomain.com
   VITE_API_URL=https://api.yourdomain.com
   ```

3. **Deploy with Docker Compose**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Run migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

## 🐳 Docker Production Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - NODE_ENV=production
    env_file:
      - ./config/.env
    volumes:
      - uploads:/app/uploads
    depends_on:
      - postgres
      - redis
      - qdrant
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    env_file:
      - ./config/.env
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./config/nginx/ssl:/etc/nginx/ssl
      - uploads:/var/www/uploads
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  uploads:
```

## 🌐 Nginx Configuration

Create `config/nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket
        location /api/ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Login rate limiting
        location /api/auth/login {
            limit_req zone=login burst=5 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # File uploads
        location /uploads/ {
            alias /var/www/uploads/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## 🔒 SSL Certificate Setup

### Using Let's Encrypt (Recommended)

1. **Install Certbot**
   ```bash
   sudo apt-get update
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. **Generate certificate**
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

3. **Auto-renewal**
   ```bash
   sudo crontab -e
   # Add this line:
   0 12 * * * /usr/bin/certbot renew --quiet
   ```

## ☁️ Cloud Platform Deployment

### AWS Deployment

#### Using ECS (Elastic Container Service)

1. **Create ECR repositories**
   ```bash
   aws ecr create-repository --repository-name multi-bot-rag/backend
   aws ecr create-repository --repository-name multi-bot-rag/frontend
   ```

2. **Build and push images**
   ```bash
   # Get login token
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

   # Build and push backend
   docker build -t multi-bot-rag/backend ./backend
   docker tag multi-bot-rag/backend:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/multi-bot-rag/backend:latest
   docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/multi-bot-rag/backend:latest

   # Build and push frontend
   docker build -t multi-bot-rag/frontend ./frontend
   docker tag multi-bot-rag/frontend:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/multi-bot-rag/frontend:latest
   docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/multi-bot-rag/frontend:latest
   ```

3. **Create ECS task definition**
   ```json
   {
     "family": "multi-bot-rag",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "backend",
         "image": "<account-id>.dkr.ecr.us-west-2.amazonaws.com/multi-bot-rag/backend:latest",
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {
             "name": "DATABASE_URL",
             "value": "postgresql://user:pass@rds-endpoint:5432/db"
           }
         ]
       }
     ]
   }
   ```

#### Using RDS for Database

1. **Create RDS instance**
   ```bash
   aws rds create-db-instance \
     --db-instance-identifier multi-bot-rag-db \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --master-username postgres \
     --master-user-password <secure-password> \
     --allocated-storage 20
   ```

### Google Cloud Platform (GCP)

#### Using Cloud Run

1. **Build and push to Container Registry**
   ```bash
   # Configure Docker for GCP
   gcloud auth configure-docker

   # Build and push backend
   docker build -t gcr.io/<project-id>/multi-bot-rag-backend ./backend
   docker push gcr.io/<project-id>/multi-bot-rag-backend

   # Build and push frontend
   docker build -t gcr.io/<project-id>/multi-bot-rag-frontend ./frontend
   docker push gcr.io/<project-id>/multi-bot-rag-frontend
   ```

2. **Deploy to Cloud Run**
   ```bash
   # Deploy backend
   gcloud run deploy multi-bot-rag-backend \
     --image gcr.io/<project-id>/multi-bot-rag-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated

   # Deploy frontend
   gcloud run deploy multi-bot-rag-frontend \
     --image gcr.io/<project-id>/multi-bot-rag-frontend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### DigitalOcean App Platform

Create `app.yaml`:

```yaml
name: multi-bot-rag-platform
services:
- name: backend
  source_dir: backend
  github:
    repo: your-username/multi-bot-rag-platform
    branch: main
  run_command: uvicorn main:app --host 0.0.0.0 --port 8080
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}
  - key: SECRET_KEY
    value: ${SECRET_KEY}

- name: frontend
  source_dir: frontend
  github:
    repo: your-username/multi-bot-rag-platform
    branch: main
  build_command: npm run build
  run_command: npm start
  environment_slug: node-js
  instance_count: 1
  instance_size_slug: basic-xxs

databases:
- name: db
  engine: PG
  version: "13"
  size: basic-xs
```

## 🔧 Environment-Specific Configurations

### Production Environment Variables

```bash
# Production .env
NODE_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Strong security
SECRET_KEY=<generate-strong-32-character-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Production database
DATABASE_URL=postgresql://user:secure_password@db-host:5432/prod_db

# Redis with password
REDIS_URL=redis://:secure_password@redis-host:6379

# Production URLs
FRONTEND_URL=https://yourdomain.com
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com

# File storage (consider cloud storage)
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=52428800  # 50MB

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
ANALYTICS_ENABLED=true
```

### Staging Environment

```bash
# Staging .env
NODE_ENV=staging
DEBUG=true
LOG_LEVEL=DEBUG

# Use staging database
DATABASE_URL=postgresql://user:password@staging-db:5432/staging_db

# Staging URLs
FRONTEND_URL=https://staging.yourdomain.com
VITE_API_URL=https://staging-api.yourdomain.com
```

## 📊 Monitoring and Logging

### Application Monitoring

1. **Health Checks**
   ```bash
   # Add to docker-compose.prod.yml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

2. **Log Aggregation**
   ```yaml
   # Add logging driver
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

### Monitoring Tools

- **Prometheus + Grafana**: For metrics and dashboards
- **ELK Stack**: For log aggregation and analysis
- **Sentry**: For error tracking
- **Uptime Robot**: For uptime monitoring

## 🔄 CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run tests
      run: |
        docker-compose -f docker-compose.test.yml up --abort-on-container-exit

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Deploy to production
      run: |
        # Add your deployment script here
        ./scripts/deploy.sh
```

## 🚨 Backup and Recovery

### Database Backup

```bash
# Create backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"

docker-compose exec postgres pg_dump -U postgres multi_bot_rag > $BACKUP_FILE
gzip $BACKUP_FILE

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_FILE.gz s3://your-backup-bucket/
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

## 🔧 Troubleshooting Production Issues

### Common Production Issues

1. **High Memory Usage**
   - Monitor vector store memory usage
   - Implement connection pooling
   - Add memory limits to containers

2. **Slow Response Times**
   - Enable Redis caching
   - Optimize database queries
   - Add CDN for static assets

3. **Database Connection Issues**
   - Check connection pool settings
   - Monitor database performance
   - Implement connection retry logic

### Performance Optimization

1. **Database Optimization**
   ```sql
   -- Add indexes for frequently queried columns
   CREATE INDEX idx_documents_user_id ON documents(user_id);
   CREATE INDEX idx_conversations_bot_id ON conversations(bot_id);
   ```

2. **Caching Strategy**
   - Cache embedding results
   - Cache frequently accessed documents
   - Implement API response caching

3. **Load Balancing**
   - Use multiple backend instances
   - Implement session affinity for WebSocket connections
   - Use database read replicas

## 📋 Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificate installed
- [ ] Database migrations run
- [ ] Backup strategy implemented
- [ ] Monitoring setup
- [ ] Log aggregation configured
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Health checks implemented
- [ ] Error tracking setup
- [ ] Performance monitoring enabled
- [ ] Documentation updated

## 🆘 Support and Maintenance

### Regular Maintenance Tasks

- **Weekly**: Review logs and performance metrics
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and update backup procedures
- **Annually**: Security audit and penetration testing

### Emergency Procedures

1. **Service Down**: Check health endpoints and logs
2. **Database Issues**: Restore from latest backup
3. **Security Breach**: Rotate secrets and review access logs
4. **Performance Issues**: Scale resources and optimize queries