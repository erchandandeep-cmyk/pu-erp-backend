# GitHub + Android APK setup

## 1. Run the backend locally
From the folder containing `manage.py`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

Web login: `http://127.0.0.1:8000/accounts/login/`

## 2. Import official department users
Log in as a user whose role is `STAFF`, `HOD` or `ADMIN`, or as a Django superuser. Open **Import Users** and upload a UTF-8 CSV.

Required columns:
`username,password,role,name`

Optional:
`user_id,email,phone,semester,section,department`

Allowed imported roles: `STUDENT`, `TEACHER`, `STAFF`, `HOD`.

Django hashes every imported password with `set_password()`.

## 3. Android API address
The emulator uses:
`http://10.0.2.2:8000/api/`

For a physical phone on the same Wi-Fi, replace `BASE_URL` in `android/app/src/main/java/com/punjabimechanical/meerp/api/Api.kt` with the PC's LAN address, e.g. `http://192.168.1.20:8000/api/`.

For real deployment, use an HTTPS domain.

## 4. Build the APK on GitHub
Push the project to a GitHub repository. Open **Actions → Build Android APK → Run workflow**.

The workflow installs Gradle on the GitHub runner and builds:
`android/app/build/outputs/apk/debug/app-debug.apk`

Download the workflow artifact named `me-erp-debug-apk`.

## 5. Before university deployment
- Use HTTPS.
- Use PostgreSQL rather than SQLite.
- Set a strong `DJANGO_SECRET_KEY` in environment variables.
- Restrict `DJANGO_ALLOWED_HOSTS` and CORS.
- Do not upload real passwords/data to GitHub.
- Configure backups and media storage.
- Add university-approved authentication and data-retention policies.
