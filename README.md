# Solve Sphere

**Solve Sphere — SIH26043 Smart India Hackathon 2026** is a platform for
connecting societal challenges with people and skills that can help solve
them. The project contains a React frontend, a FastAPI backend, MongoDB-backed
authentication and profile management, and challenge analysis and student
matching features.

## Features

- Email/password registration and login, plus optional Google Sign-In.
- User profiles with optional information that can be completed or updated
  after registration.
- Role-based access for students, problem owners, mentors, faculty, and
  administrators.
- Challenge analysis and matching for relevant student skills.
- API and database health endpoints.

## Technology

- **Frontend:** React, Vite, React Router, Axios
- **Backend:** Python, FastAPI, PyMongo, PyJWT
- **Database:** MongoDB
- **Matching:** sentence-transformers embeddings and challenge analysis

## Prerequisites

- Node.js and npm
- Python 3.11 or newer
- MongoDB running locally or a MongoDB connection URI
- Google OAuth Web Client ID only if you want to enable Google Sign-In

## Setup

Run commands from the project root in PowerShell.

### 1. Configure the backend

Create a virtual environment, install dependencies, and copy the example
configuration:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set at least:

```dotenv
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=solve_sphere
JWT_SECRET_KEY=replace-with-a-random-secret-of-at-least-32-characters
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Generate a secure JWT secret in PowerShell if needed:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

To enable Google Sign-In, also set `GOOGLE_CLIENT_ID` to your Google OAuth
**Web application Client ID**. Do not put a Google client secret in the frontend
or in a `VITE_` variable.

### 2. Configure the frontend

In a second PowerShell terminal, from the project root:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
```

Set these values in `frontend/.env`:

```dotenv
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

The frontend and backend Google Client IDs must be the same. The Client ID is
public; never place private credentials or a client secret in frontend
environment variables. Local `.env` files are ignored by Git.

For Google Cloud Console setup, authorized origins, and the Google Identity
Services popup flow, see [AUTHENTICATION_SETUP.md](./AUTHENTICATION_SETUP.md).
Google Sign-In is optional; email/password authentication works without Google
OAuth configuration.

## Run locally

Start MongoDB before launching the backend. In one terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm run dev
```

Open the frontend URL printed by Vite (usually `http://localhost:5173`).
Interactive API documentation is available at
`http://localhost:8000/docs`; backend health is at
`http://localhost:8000/api/health` and database health at
`http://localhost:8000/api/health/database`.

## Tests and production build

Run the backend test suite from the project root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Build the frontend:

```powershell
cd frontend
npm run build
```

## Main API routes

All routes are prefixed with `/api`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register/{role}` | Register a user |
| `POST` | `/auth/login` | Sign in with email and password |
| `POST` | `/auth/google` | Verify a Google ID token and sign in |
| `GET` | `/auth/me` | Get the current user's profile |
| `PATCH` | `/auth/me` | Update profile information |
| `POST` | `/auth/logout` | Revoke the current session token |
| `POST` | `/matching/analyze` | Analyze a challenge |
| `POST` | `/matching/students` | Find matching students |
| `GET` | `/health` | Check API health |
| `GET` | `/health/database` | Check MongoDB connectivity |

Authentication-protected routes require a bearer access token.

## Repository safety

Do not commit `.env` files, passwords, signing secrets, database credentials,
Google client secrets, virtual environments, or dependency build output. Use
the checked-in `.env.example` templates for configuration references.
