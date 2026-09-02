# Development Guide — AI Revenue Recovery Platform

---

## Overview

This document outlines the intended local development workflow. 

**Note: The application code does not exist yet. The commands below are placeholders illustrating the target workflow once the foundation is implemented.**

---

## Prerequisites

- **Python:** 3.11 or higher
- **PostgreSQL:** 15 or higher
- **Git:** For version control
- **Razorpay Account:** A test mode account for API credentials

---

## Local Setup (Intended Workflow)

### 1. Clone the Repository
```bash
git clone <repository_url>
cd REVISQ
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
# TODO: pip install -r requirements.txt (once created)
```

### 4. Configure Environment Variables
Copy the example environment file and fill in your local values:
```bash
cp .env.example .env
```
Edit `.env` to include your PostgreSQL credentials, Razorpay Test Mode keys, and AI provider API key.

### 5. Setup Database
Ensure PostgreSQL is running and create the local database:
```bash
# Example
createdb revenue_recovery_db
```

Run migrations:
```bash
# TODO: python manage.py migrate (once Django is initialized)
```

### 6. Create Superuser
```bash
# TODO: python manage.py createsuperuser (once Django is initialized)
```

### 7. Run Development Server
```bash
# TODO: python manage.py runserver (once Django is initialized)
```

Access the Django Admin panel at `http://localhost:8000/admin/`.

---

## Running Tests (Intended Workflow)

The project will use `pytest` for the test suite.

```bash
# TODO: pytest (once test suite is established)
```

---

## Code Quality

The project intends to use standard Python linting and formatting tools:
- **Black** for code formatting
- **Ruff** or **Flake8** for linting
- **Mypy** for static type checking

---

## Git Workflow

- The main branch is `main`.
- Feature branches should be created for all new work.
- Use Conventional Commits style for commit messages:
  - `feat: add AI decision engine`
  - `fix: correct retry logic in guardrail`
  - `docs: update evaluation metrics`

---

## Adding New Django Apps

If adding a new logical module, create a new Django app inside the `apps/` directory to maintain the modular monolith structure:

```bash
# TODO: python manage.py startapp <app_name> apps/<app_name>
```
Remember to register the new app in `config/settings.py`.
