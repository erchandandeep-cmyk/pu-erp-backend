# ME-ERP — Mechanical Engineering Department

Punjabi University Patiala departmental ERP prototype built with Django REST Framework and a native Android (Kotlin + Jetpack Compose) client.

## Core features
- User ID/password login with token authentication.
- Role-based users: Student, Teacher, Staff, HOD and Department Admin.
- Department Office CSV import for authorized Staff/HOD/Admin users.
- Application submission and status tracking.
- Department-side application processing.
- Role-filtered announcements.
- Android client connected to the Django API.
- GitHub Actions workflow to build a debug APK without Android Studio.

## CSV import
Required columns:
`username,password,role,name`

Optional columns:
`user_id,email,phone,semester,section,department`

Allowed imported roles: `STUDENT`, `TEACHER`, `STAFF`, `HOD`.

Passwords are hashed by Django during import. Never commit the original CSV to GitHub.

## Local backend
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Web login: `http://127.0.0.1:8000/accounts/login/`
API: `http://127.0.0.1:8000/api/`

## Android
The emulator is configured for `http://10.0.2.2:8000/api/`. A physical phone needs a reachable LAN/deployed HTTPS address. Update `BASE_URL` in `android/app/src/main/java/com/punjabimechanical/meerp/api/Api.kt` before installing on a physical device.

## GitHub APK
Push the repository to GitHub. Open **Actions → Build Android APK → Run workflow**. The resulting `app-debug.apk` is uploaded as a workflow artifact.

For production, deploy Django behind HTTPS, use PostgreSQL, configure `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, CORS, backups, and a proper domain/server.
