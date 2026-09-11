import csv
import io

from django.db import transaction

from .models import User
from organizations.models import OrgUnit


# Required CSV columns
REQUIRED_COLUMNS = {
    "username",
    "password",
    "role",
    "name",
}


def get_role_mapping():
    """
    Creates a case-insensitive mapping between the role written
    in the CSV file and the actual Django User.Role value.
    """

    mapping = {}

    for choice in User.Role.choices:
        value = str(choice[0]).strip()
        label = str(choice[1]).strip()

        mapping[value.upper()] = value
        mapping[label.upper()] = value

    return mapping


def import_users_from_csv(uploaded_file, actor):
    """
    Import students, teachers, staff and HOD users from CSV.

    Required columns:
        username
        password
        role
        name

    Optional columns:
        user_id
        email
        phone
        department
        org_unit_code
        semester
        section
    """

    # ---------------------------------------------------------
    # READ CSV FILE
    # ---------------------------------------------------------

    try:
        text = uploaded_file.read().decode("utf-8-sig")

    except UnicodeDecodeError as exc:
        raise ValueError(
            "CSV must be UTF-8 encoded."
        ) from exc

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError(
            "CSV is empty or has no header row."
        )

    # ---------------------------------------------------------
    # CLEAN HEADER NAMES
    # ---------------------------------------------------------

    headers = {
        str(header).strip().lower()
        for header in reader.fieldnames
        if header
    }

    missing = REQUIRED_COLUMNS - headers

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    # ---------------------------------------------------------
    # CREATE ROLE MAPPING
    # ---------------------------------------------------------

    role_mapping = get_role_mapping()

    # ---------------------------------------------------------
    # COUNTERS
    # ---------------------------------------------------------

    created = 0
    updated = 0
    errors = []

    rows = list(reader)

    # ---------------------------------------------------------
    # DATABASE TRANSACTION
    # ---------------------------------------------------------

    with transaction.atomic():

        for line_no, raw in enumerate(rows, start=2):

            # ---------------------------------------------
            # CLEAN EACH ROW
            # ---------------------------------------------

            row = {}

            for key, value in raw.items():

                if key:

                    clean_key = str(key).strip().lower()

                    clean_value = (
                        str(value).strip()
                        if value is not None
                        else ""
                    )

                    row[clean_key] = clean_value

            # ---------------------------------------------
            # BASIC INFORMATION
            # ---------------------------------------------

            username = row.get("username", "").strip()

            password = row.get("password", "").strip()

            name = row.get("name", "").strip()

            role_input = row.get("role", "").strip()

            # ---------------------------------------------
            # REQUIRED FIELD CHECK
            # ---------------------------------------------

            if not username:

                errors.append(
                    f"Line {line_no}: username is required."
                )

                continue

            if not password:

                errors.append(
                    f"Line {line_no}: password is required."
                )

                continue

            if not name:

                errors.append(
                    f"Line {line_no}: name is required."
                )

                continue

            if not role_input:

                errors.append(
                    f"Line {line_no}: role is required."
                )

                continue

            # ---------------------------------------------
            # ROLE CONVERSION
            # ---------------------------------------------

            role_key = role_input.upper()

            role = role_mapping.get(role_key)

            if role is None:

                errors.append(
                    f"Line {line_no}: invalid role "
                    f"'{role_input}'. "
                    f"Allowed imported roles: "
                    f"STUDENT, TEACHER, STAFF, HOD."
                )

                continue

            # ---------------------------------------------
            # DO NOT IMPORT ADMIN
            # ---------------------------------------------

            admin_role = getattr(
                User.Role,
                "ADMIN",
                None
            )

            if admin_role is not None:

                admin_value = getattr(
                    admin_role,
                    "value",
                    str(admin_role)
                )

                if role == admin_value:

                    errors.append(
                        f"Line {line_no}: ADMIN users "
                        f"cannot be imported from CSV."
                    )

                    continue

            # ---------------------------------------------
            # PASSWORD LENGTH
            # ---------------------------------------------

            if len(password) < 8:

                errors.append(
                    f"Line {line_no}: password must "
                    f"be at least 8 characters."
                )

                continue

            # ---------------------------------------------
            # NAME
            # ---------------------------------------------

            name_parts = name.split(None, 1)

            first_name = name_parts[0]

            last_name = (
                name_parts[1]
                if len(name_parts) > 1
                else ""
            )

            # ---------------------------------------------
            # SEMESTER
            # ---------------------------------------------

            semester_value = row.get(
                "semester",
                ""
            ).strip()

            if semester_value.isdigit():

                semester = int(semester_value)

            else:

                semester = None

            # ---------------------------------------------
            # ORG UNIT (department / college / office)
            # ---------------------------------------------

            org_unit_code = row.get("org_unit_code", "").strip().upper()

            org_unit = None

            if org_unit_code:

                org_unit = OrgUnit.objects.filter(code=org_unit_code).first()

                if org_unit is None:

                    errors.append(
                        f"Line {line_no}: org_unit_code "
                        f"'{org_unit_code}' does not match any "
                        f"existing organisation unit - user was "
                        f"still created/updated, just without a "
                        f"linked org unit."
                    )

            # ---------------------------------------------
            # USER DEFAULTS
            # ---------------------------------------------

            defaults = {

                "first_name": first_name,

                "last_name": last_name,

                "email": row.get(
                    "email",
                    ""
                ).strip(),

                "role": role,

                "employee_or_student_id": row.get(
                    "employee_or_student_id",
                    row.get(
                        "user_id",
                        username
                    )
                ).strip(),

                "phone": row.get(
                    "phone",
                    ""
                ).strip(),

                "department": row.get(
                    "department",
                    "Mechanical Engineering"
                ).strip(),

                "org_unit": org_unit,

                "semester": semester,

                "section": row.get(
                    "section",
                    ""
                ).strip(),

                "is_active": True,

                "is_active_account": True,
            }

            # ---------------------------------------------
            # FIND EXISTING USER
            # ---------------------------------------------

            user = User.objects.filter(
                username__iexact=username
            ).first()

            # ---------------------------------------------
            # CREATE USER
            # ---------------------------------------------

            if user is None:

                user = User(
                    username=username,
                    **defaults
                )

                user.set_password(password)

                user.save()

                created += 1

            # ---------------------------------------------
            # UPDATE EXISTING USER
            # ---------------------------------------------

            else:

                for key, value in defaults.items():

                    setattr(
                        user,
                        key,
                        value
                    )

                user.set_password(password)

                user.save()

                updated += 1

    # ---------------------------------------------------------
    # RETURN RESULT
    # ---------------------------------------------------------

    return {

        "created": created,

        "updated": updated,

        "errors": errors,

        "total_rows": len(rows),

        "imported": created + updated,

    }