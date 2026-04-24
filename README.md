# EasyTap AI Backend

Backend for the EasyTap AI frontend built with Django, Django REST Framework, and JWT authentication.

## Features

- Custom user model with `student` / `admin` roles
- JWT auth via `djangorestframework-simplejwt`
- Student profile and skills management
- External job sourcing from HH + Remotive with demo fallback
- Admin candidates endpoint for recruiters
- CORS configured for local frontend development

## Project structure

- `config/` - Django project settings and root URLs
- `accounts/` - auth, profile, skills, jobs, and admin candidate APIs

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and adjust values if needed.
4. Run migrations:

```bash
python manage.py migrate
```

5. Start the development server:

```bash
python manage.py runserver
```

API base URL: `http://localhost:8000/api/`

Frontend base URL should be configured as:

```env
VITE_API_URL=http://localhost:8000/api
```

## Google OAuth setup

To enable "Continue with Google", configure an OAuth client in Google Cloud Console.

Authorized redirect URI:

```text
http://localhost:8000/api/auth/google/callback/
```

Then set these environment variables in backend `.env`:

```env
BACKEND_BASE_URL=http://localhost:8000
FRONTEND_GOOGLE_CALLBACK_URL=http://localhost:8080/auth/callback
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback/
```

## Groq AI chat setup

This project now uses Groq for the student assistant chat through the backend endpoint:

```text
POST /api/assistant/chat/
```

Add your Groq API key to backend `.env`:

```env
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
HH_API_URL=https://api.hh.ru
REMOTIVE_API_URL=https://remotive.com/api
JOB_SEARCH_TIMEOUT=12
```

Then restart Django.
