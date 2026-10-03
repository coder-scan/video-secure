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
+-----------------------+             +-------+-------------------------+
                                              |                     ^
                                              v                     |
                                      +-------+-------+             |
                                      | Managed Redis |             |
                                      +-------+-------+             |
                                              |                     |
                                      Task Queue Events             |
                                              |                     |
                                              v                     |
                                      +-------+---------------------+---+
                                      | Celery Worker (FFmpeg)          |
                                      | (secure-video-worker)           |
                                      +---------------------------------+
```

---

## Method 1: 1-Click Blueprint Deployment (Recommended)

Render Blueprints automatically spin up all services, database, Redis, environment variables, and connections in one step via [`render.yaml`](./render.yaml).

### Steps:
1. **Push your code** to GitHub or GitLab.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Blueprint**.
4. Connect your Git repository.
5. Render will detect `render.yaml` and list all 5 components:
   - `secure-video-db` (PostgreSQL Database)
   - `secure-video-redis` (Key-Value Redis instance)
   - `secure-video-backend` (FastAPI Control Plane)
   - `secure-video-worker` (Celery + FFmpeg Transcoding Worker)
   - `secure-video-frontend` (Next.js Creator Studio & Player)
6. Click **Apply**.
7. Render will automatically generate secure encryption keys (`SECRET_KEY`, `MASTER_ENCRYPTION_KEY`) and link your database and Redis URLs.

---

## Method 2: Manual Dashboard Setup

If you prefer provisioning services individually in the Render UI:

### Step 1: Create PostgreSQL Database
1. Click **New +** > **PostgreSQL**.
2. **Name**: `secure-video-db`
3. **Database**: `secure_video_db`
4. **User**: `secure_video_user`
5. **Plan**: `Free` (or `Starter`)
6. Copy the **Internal Database URL** once created.

### Step 2: Create Redis Instance
1. Click **New +** > **Redis**.
2. **Name**: `secure-video-redis`
3. **Plan**: `Free` (or `Starter`)
4. **Maxmemory Policy**: `noeviction`
5. Copy the **Internal Redis URL** once created.

### Step 3: Deploy Backend (Web Service)
1. Click **New +** > **Web Service**.
2. Connect your Git repository.
3. Configure settings:
   - **Name**: `secure-video-backend`
   - **Language / Runtime**: `Docker`
   - **Docker Context**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Health Check Path**: `/health`
4. Under **Environment Variables**, add:
   ```env
   ENVIRONMENT=production
   DEBUG=False
   PORT=8000
   DATABASE_URL=<Paste Internal Database URL from Step 1>
   REDIS_URL=<Paste Internal Redis URL from Step 2>
   CELERY_BROKER_URL=<Paste Internal Redis URL from Step 2>
   CELERY_RESULT_BACKEND=<Paste Internal Redis URL from Step 2>
   SECRET_KEY=<Click Generate or enter 64-char random string>
   MASTER_ENCRYPTION_KEY=<Enter 32-char hex string>
   STORAGE_PROVIDER_TYPE=LOCAL
   LOCAL_STORAGE_BASE_PATH=./storage
   CORS_ORIGINS=https://<your-frontend-name>.onrender.com,http://localhost:3000
   ```
5. Click **Deploy Web Service**.

### Step 4: Deploy Celery Worker (Background Worker)
1. Click **New +** > **Background Worker**.
2. Connect the same Git repository.
3. Configure settings:
   - **Name**: `secure-video-worker`
   - **Language / Runtime**: `Docker`
   - **Docker Context**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Command**: `celery -A app.celery_app worker --loglevel=info -c 2`
4. Add the same environment variables as the backend (`DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `SECRET_KEY`, `MASTER_ENCRYPTION_KEY`, etc.).
5. Click **Deploy Background Worker**.

> **Note on Free Tier**: Render Background Workers require a paid tier ($7/mo). If you are on the Render **Free Tier**, the backend has an automated in-process async processing fallback (`asyncio.create_task`), so you can run the entire platform without a separate background worker!

### Step 5: Deploy Frontend (Web Service)
1. Click **New +** > **Web Service**.
2. Connect your Git repository.
3. Configure settings:
   - **Name**: `secure-video-frontend`
   - **Root Directory**: `frontend`
   - **Runtime**: `Node`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`
4. Under **Environment Variables**, add:
   ```env
   NODE_ENV=production
   NEXT_PUBLIC_API_URL=https://secure-video-backend.onrender.com
   ```
   *(Replace with your actual backend Render URL)*
5. Click **Deploy Web Service**.

---

## Cloud Storage Setup (Cloudflare R2 / AWS S3)

For scalable production video hosting (without relying on local disk storage):

1. Set the following environment variables in both `secure-video-backend` and `secure-video-worker`:
   ```env
   STORAGE_PROVIDER_TYPE=S3
   S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com  # or AWS S3 endpoint
   S3_ACCESS_KEY_ID=<YOUR_ACCESS_KEY>
   S3_SECRET_ACCESS_KEY=<YOUR_SECRET_KEY>
   S3_REGION_NAME=auto
   S3_BUCKET_NAME=<YOUR_BUCKET_NAME>
   ```
2. Video uploads will stream directly to your bucket via presigned multipart uploads with 0 server bandwidth hops.

---

## Verification & Health Check

After deployment completes:

1. **Backend Health Check**:
   Visit `https://<backend-url>.onrender.com/health`
   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "Secure Video Infrastructure & Anti-Piracy Platform",
     "environment": "production"
   }
   ```

2. **API Interactive Documentation**:
   Visit `https://<backend-url>.onrender.com/docs` to test endpoints via Swagger UI.

3. **Creator Studio & Web Player**:
   Open `https://<frontend-url>.onrender.com` in your browser:
   - Register a new organization / login.
   - Upload a sample video (`.mp4` / `.mov` / `.webm`).
   - Monitor real-time status transitions (`UPLOADING` -> `QUEUED` -> `PROCESSING` -> `READY`).
   - Play the encrypted multi-bitrate HLS stream with anti-piracy dynamic watermark.
