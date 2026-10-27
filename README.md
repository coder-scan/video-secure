# video-secure

## Secure Video Infrastructure & Anti-Piracy Platform

A high-performance platform for secure video hosting, streaming, anti-piracy intelligence, dynamic watermarking, and centralized quota management.

---

## Architecture Overview

The system strictly divides concerns into three decoupled tiers:

1. **Control Plane (FastAPI + PostgreSQL / SQLite)**:
   - Tenant isolation & Organization management
   - Authentication (Argon2id) & RBAC (`OWNER`, `ADMIN`, `CREATOR`, `VIEWER`)
   - Centralized Quota & Usage Engine (Storage, Video Count, Processing Minutes, Bandwidth)
   - Playback token issuance & license key gating
   - Session & device concurrency enforcement

2. **Processing Plane (Asynchronous FFmpeg Pipeline)**:
   - Asynchronous media container inspection (`ffprobe`)
   - Multi-bitrate HLS packaging (Adaptive Bitrate Streaming)
   - AES-128 cryptographic key & IV generation
   - Automated thumbnail extraction and metadata profiling

3. **Delivery Plane (Local Storage + Google Drive BYOS + Secure Player)**:
   - Direct-to-storage upload and Google Drive BYOS integration
   - Encrypted HLS segment streaming
   - Zero-trust playback token handshake
   - Dynamic canvas watermarking with tamper-evident watchdog

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run automated tests
pytest -v

# Run FastAPI backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API Documentation will be available at: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Creator Studio will be available at: `http://localhost:3000`

---

## Automated Verification

All components are verified via automated Pytest suites:
* Health checks
* Tenant & user registration
* Argon2id password hashing & JWT auth
* Tenant quota allocations & usage ledger
* Direct upload intent & presigned URL generation
* Storage quota hard-limit enforcement
* Google Drive BYOS integration & quota expansion
* Multi-tenant IDOR boundary isolation

---

## Production Deployment (Render.com)

The project includes ready-to-use Render Blueprint configuration ([`render.yaml`](./render.yaml)) supporting FastAPI backend, PostgreSQL database, and Next.js frontend.

For complete instructions, see the [Render Deployment Guide](./RENDER_DEPLOYMENT.md).
