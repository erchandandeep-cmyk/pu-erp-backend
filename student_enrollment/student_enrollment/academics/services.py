import csv
import io

import openpyxl
from django.core.exceptions import ValidationError

from accounts.models import User
from .models import AcademicSession, Programme, Enrollment

REQUIRED_COLUMNS = {"student_username", "programme_code", "academic_session", "batch_year"}


def _process_enrollment_rows(rows):
    created, updated, errors = 0, 0, []

    for i, raw in enumerate(rows, start=2):  # row 1 is the header
        row = {}
        for key, value in raw.items():
            if key:
                clean_key = str(key).strip().lower()
                row[clean_key] = str(value).strip() if value is not None else ""

        username = row.get("student_username", "")
        programme_code = row.get("programme_code", "").strip().upper()
        session_name = row.get("academic_session", "").strip()
        batch_year = row.get("batch_year", "").strip()
        roll_number = row.get("roll_number", "").strip()
        semester = row.get("current_semester", "1").strip() or "1"
        status = (row.get("status", "ACTIVE").strip().upper()) or "ACTIVE"

        if not username or not programme_code or not session_name or not batch_year:
            errors.append(
                f"Line {i}: student_username, programme_code, academic_session, "
                f"and batch_year are all required."
            )
            continue

        student = User.objects.filter(username__iexact=username, role=User.Role.STUDENT).first()
        if student is None:
            errors.append(f"Line {i}: no student with username '{username}' found.")
            continue

        programme = Programme.objects.filter(code=programme_code).first()
        if programme is None:
            errors.append(f"Line {i}: no programme with code '{programme_code}' found.")
            continue

        session = AcademicSession.objects.filter(name=session_name).first()
        if session is None:
            errors.append(f"Line {i}: no academic session named '{session_name}' found.")
            continue

        if not batch_year.isdigit():
            errors.append(f"Line {i}: batch_year '{batch_year}' must be a number.")
            continue

        if status not in Enrollment.Status.values:
            errors.append(
                f"Line {i}: status '{status}' is invalid. "
                f"Allowed: {', '.join(Enrollment.Status.values)}"
            )
            continue

        if not semester.isdigit():
            errors.append(f"Line {i}: current_semester '{semester}' must be a number.")
            continue

        obj, was_created = Enrollment.objects.update_or_create(
            student=student,
            programme=programme,
            academic_session=session,
            defaults={
                "batch_year": int(batch_year),
                "roll_number": roll_number,
                "current_semester": int(semester),
                "status": status,
            },
        )
        try:
            obj.full_clean()
        except ValidationError as exc:
            errors.append(f"Line {i}: {'; '.join(exc.messages)}")
            obj.delete() if was_created else None
            continue

        created += was_created
        updated += not was_created

    return {"created": created, "updated": updated, "errors": errors, "total_rows": len(rows)}


def import_enrollments_from_csv(uploaded_file):
    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or has no header row.")
    missing = REQUIRED_COLUMNS - {h.strip().lower() for h in reader.fieldnames}
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(sorted(missing)))

    return _process_enrollment_rows(list(reader))


def import_enrollments_from_excel(uploaded_file):
    try:
        workbook = openpyxl.load_workbook(uploaded_file, data_only=True, read_only=True)
    except Exception as exc:
        raise ValueError("Could not read this as a valid .xlsx file.") from exc

    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise ValueError("The Excel file is empty.")

    fieldnames = [str(h).strip().lower() if h is not None else "" for h in header_row]
    missing = REQUIRED_COLUMNS - set(fieldnames)
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(sorted(missing)))

    rows = []
    for values in rows_iter:
        if values is None or all(v is None or str(v).strip() == "" for v in values):
            continue
        rows.append({k: ("" if v is None else v) for k, v in zip(fieldnames, values) if k})

    return _process_enrollment_rows(rows)
