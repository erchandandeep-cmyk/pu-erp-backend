import csv
import io

import openpyxl
from django.db import transaction

from .models import User
from organizations.models import OrgUnit


# Required columns (CSV and Excel both use these same names)
REQUIRED_COLUMNS = {
    "username",
    "password",
    "role",
    "name",
}


def get_role_mapping():
    """
    Creates a case-insensitive mapping between the role written
    in the file and the actual Django User.Role value.
    """

    mapping = {}

    for choice in User.Role.choices:
        value = str(choice[0]).strip()
        label = str(choice[1]).strip()

        mapping[value.upper()] = value
        mapping[label.upper()] = value

    return mapping


def _process_user_rows(rows, actor):
    """
    Shared row-processing logic used by both the CSV and Excel
    importers, so the two file formats behave identically. `rows` is a
    list of dicts (already one dict per data row, any casing/spacing).

    Required columns:
        username
        password
        role
        name

    Optional columns:
        user_id
        email
        phone
        designation
        department
        org_unit_code
        semester
        section
    """

    role_mapping = get_role_mapping()

    created = 0
    updated = 0
    errors = []

    with transaction.atomic():

        for line_no, raw in enumerate(rows, start=2):  # row 1 is the header

            row = {}
            for key, value in raw.items():
                if key:
                    clean_key = str(key).strip().lower()
                    clean_value = str(value).strip() if value is not None else ""
                    row[clean_key] = clean_value

            username = row.get("username", "").strip()
            password = row.get("password", "").strip()
            name = row.get("name", "").strip()
            role_input = row.get("role", "").strip()

            if not username:
                errors.append(f"Line {line_no}: username is required.")
                continue
            if not password:
                errors.append(f"Line {line_no}: password is required.")
                continue
            if not name:
                errors.append(f"Line {line_no}: name is required.")
                continue
            if not role_input:
                errors.append(f"Line {line_no}: role is required.")
                continue

            role_key = role_input.upper()
            role = role_mapping.get(role_key)

            if role is None:
                errors.append(
                    f"Line {line_no}: invalid role '{role_input}'. "
                    f"Allowed: STUDENT, TEACHER, STAFF, HOD, ADMIN."
                )
                continue

            # ADMIN accounts (e.g. VC, Registrar, Deans) can only be
            # created by someone who is themselves an Admin/Superuser -
            # prevents a Staff/HOD account from self-escalating via a
            # crafted upload.
            admin_role = getattr(User.Role, "ADMIN", None)
            if admin_role is not None:
                admin_value = getattr(admin_role, "value", str(admin_role))
                actor_is_admin = bool(
                    actor and (getattr(actor, "is_superuser", False) or getattr(actor, "role", None) == admin_value)
                )
                if role == admin_value and not actor_is_admin:
                    errors.append(
                        f"Line {line_no}: ADMIN users can only be imported by an Admin/Superuser."
                    )
                    continue

            if len(password) < 8:
                errors.append(f"Line {line_no}: password must be at least 8 characters.")
                continue

            name_parts = name.split(None, 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            semester_value = row.get("semester", "").strip()
            semester = int(semester_value) if semester_value.isdigit() else None

            org_unit_code = row.get("org_unit_code", "").strip().upper()
            org_unit = None
            if org_unit_code:
                org_unit = OrgUnit.objects.filter(code=org_unit_code).first()
                if org_unit is None:
                    errors.append(
                        f"Line {line_no}: org_unit_code '{org_unit_code}' does not match "
                        f"any existing organisation unit - user was still created/updated, "
                        f"just without a linked org unit."
                    )

            defaults = {
                "first_name": first_name,
                "last_name": last_name,
                "email": row.get("email", "").strip(),
                "role": role,
                "employee_or_student_id": row.get(
                    "employee_or_student_id", row.get("user_id", username)
                ).strip(),
                "phone": row.get("phone", "").strip(),
                "designation": row.get("designation", "").strip(),
                "department": row.get("department", "Mechanical Engineering").strip(),
                "org_unit": org_unit,
                "semester": semester,
                "section": row.get("section", "").strip(),
                "is_active": True,
                "is_active_account": True,
            }

            user = User.objects.filter(username__iexact=username).first()

            if user is None:
                user = User(username=username, **defaults)
                user.set_password(password)
                user.save()
                created += 1
            else:
                for key, value in defaults.items():
                    setattr(user, key, value)
                user.set_password(password)
                user.save()
                updated += 1

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_rows": len(rows),
        "imported": created + updated,
    }


def import_users_from_csv(uploaded_file, actor):
    """Import users from a .csv file. See _process_user_rows for columns."""

    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV is empty or has no header row.")

    headers = {str(h).strip().lower() for h in reader.fieldnames if h}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

    rows = list(reader)
    return _process_user_rows(rows, actor)


def import_users_from_excel(uploaded_file, actor):
    """
    Import users from a .xlsx file - same columns/behaviour as the CSV
    importer, for offices that prefer working in Excel. The first row
    must be the header row with the same column names as the CSV.
    """

    try:
        workbook = openpyxl.load_workbook(uploaded_file, data_only=True, read_only=True)
    except Exception as exc:
        raise ValueError(
            "Could not read this file as an Excel (.xlsx) workbook. "
            "Make sure it's a real .xlsx file, not a renamed .csv or .xls."
        ) from exc

    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)

    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise ValueError("The Excel file is empty.")

    fieldnames = [str(h).strip().lower() if h is not None else "" for h in header_row]
    missing = REQUIRED_COLUMNS - set(fieldnames)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

    rows = []
    for values in rows_iter:
        if values is None or all(v is None or str(v).strip() == "" for v in values):
            continue  # skip fully blank rows (common at the end of a sheet)
        row = {}
        for key, value in zip(fieldnames, values):
            if key:
                row[key] = "" if value is None else value
        rows.append(row)

    return _process_user_rows(rows, actor)
