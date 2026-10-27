# Deploying Secure Video Infrastructure on Render.com

This project is fully configured and ready for production deployment on [Render](https://render.com).

---

## Architecture on Render

```
                                      +---------------------------------+
                                      |     Next.js Web Service         |
                                      |    (secure-video-frontend)      |
                                      +----------------+----------------+
                                                       |
                                            HTTPS / API Ingestion
                                                       |
                                                       v
+-----------------------+             +----------------+----------------+
|  Managed PostgreSQL   | <---------+ |      FastAPI Web Service        |
|   (secure-video-db)   |             |     (secure-video-backend)      |
+-----------------------+             +---------------------------------+
```

---

## Method 1: 1-Click Blueprint Deployment (Recommended)

Render Blueprints automatically spin up all services, database, environment variables, and connections in one step via [`render.yaml`](./render.yaml).

### Steps:
1. **Push your code** to GitHub or GitLab.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Blueprint**.
4. Connect your Git repository.
5. Render will detect `render.yaml` and list all components:
   - `secure-video-db` (PostgreSQL Database)
   - `secure-video-backend` (FastAPI Control Plane)
   - `secure-video-frontend` (Next.js Creator Studio & Player)
6. Click **Apply**.
7. Render will automatically generate secure encryption keys (`SECRET_KEY`, `MASTER_ENCRYPTION_KEY`) and link your database URL.

---

## Method 2: Manual Dashboard Setup

If you prefer to configure services individually in the Render dashboard:

### 1. PostgreSQL Database
- Name: `secure-video-db`
- Plan: Free
- Copy Internal Database URL after creation.

### 2. FastAPI Backend
- Type: Web Service
- Environment: Docker
- Root Directory: `backend`
- Health Check Path: `/health`
- Environment Variables:
  - `DATABASE_URL`: `[Internal Database URL from Step 1]`
  - `ENVIRONMENT`: `production`
  - `DEBUG`: `false`
  - `STORAGE_PROVIDER_TYPE`: `LOCAL`

### 3. Next.js Frontend
- Type: Web Service
- Environment: Node
- Root Directory: `frontend`
- Build Command: `npm install && npm run build`
- Start Command: `npm start`
- Environment Variables:
  - `NEXT_PUBLIC_API_URL`: `https://[your-backend-url].onrender.com/api/v1`
