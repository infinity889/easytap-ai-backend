# EasyTap AI Backend

Backend for the EasyTap AI frontend built with Django, Django REST Framework, and JWT authentication.

## Features

- Custom user model with `student` / `admin` roles
- JWT auth via `djangorestframework-simplejwt`
- Student profile and skills management
- Demo job match recommendations
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
