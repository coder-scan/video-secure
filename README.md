# Secure Video Infrastructure & Anti-Piracy Platform

A high-performance platform for secure video hosting, streaming, anti-piracy intelligence, dynamic watermarking, and centralized quota management.

---

## Architecture Overview

The system strictly divides concerns into three decoupled tiers:

1. **Control Plane (FastAPI + PostgreSQL + Redis)**:
   - Tenant isolation & Organization management
   - Authentication (Argon2id) & RBAC (`OWNER`, `ADMIN`, `CREATOR`, `VIEWER`)
   - Centralized Quota & Usage Engine (Storage, Video Count, Processing Minutes, Bandwidth)
   - Playback token issuance & license key gating
   - Session & device concurrency enforcement

2. **Processing Plane (Celery + FFmpeg)**:
   - Asynchronous media container inspection (`ffprobe`)
   - Multi-bitrate HLS packaging (Adaptive Bitrate Streaming)
   - AES-128 cryptographic key & IV generation
   - Automated thumbnail extraction and metadata profiling

3. **Delivery Plane (Private Storage + Cloudflare CDN + Secure Player)**:
   - Direct-to-storage presigned multipart uploads (Zero server hop)
   - HLS segment streaming via Cloudflare CDN
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

All Stage 1 components are verified via automated Pytest suites:
* Health checks
* Tenant & user registration
* Argon2id password hashing & JWT auth
* Tenant quota allocations & usage ledger
* Direct upload intent & presigned URL generation
* Storage quota hard-limit enforcement
* Multi-tenant IDOR boundary isolation
