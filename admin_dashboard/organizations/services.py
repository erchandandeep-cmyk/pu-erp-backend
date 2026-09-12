import csv
import io

from .models import OrgUnit

VALID_TYPES = {c[0] for c in OrgUnit.UnitType.choices}

REQUIRED_COLUMNS = {"code", "name", "unit_type"}


def import_org_units_from_csv(uploaded_file):
    """
    Bulk import/update Organisation Units from an uploaded CSV file
    (a Django UploadedFile - already-open file objects also work).

    Required columns: code,name,unit_type
    Optional columns: parent_code,contact_email,contact_phone,address

    Safe to run repeatedly with the same file - existing codes are
    updated, not duplicated. Returns a dict with counts and any
    per-row problems (row problems don't stop the rest of the import).
    """

    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV is empty or has no header row.")

    missing = REQUIRED_COLUMNS - {h.strip().lower() for h in reader.fieldnames}
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(missing)}")

    rows = list(reader)
    created, updated, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        code = (row.get("code") or "").strip().upper()
        name = (row.get("name") or "").strip()
        unit_type = (row.get("unit_type") or "").strip().upper()

        if not code or not name:
            errors.append(f"Line {i}: 'code' and 'name' are required.")
            continue
        if unit_type not in VALID_TYPES:
            errors.append(
                f"Line {i}: unit_type '{unit_type}' is invalid. "
                f"Allowed: {', '.join(sorted(VALID_TYPES))}"
            )
            continue

        obj, was_created = OrgUnit.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "unit_type": unit_type,
                "contact_email": (row.get("contact_email") or "").strip(),
                "contact_phone": (row.get("contact_phone") or "").strip(),
                "address": (row.get("address") or "").strip(),
            },
        )
        created += was_created
        updated += not was_created

    # Second pass: link parents, so row order in the CSV doesn't matter.
    for row in rows:
        code = (row.get("code") or "").strip().upper()
        parent_code = (row.get("parent_code") or "").strip().upper()
        if not code or not parent_code:
            continue
        try:
            unit = OrgUnit.objects.get(code=code)
            parent = OrgUnit.objects.get(code=parent_code)
        except OrgUnit.DoesNotExist:
            errors.append(
                f"Could not link '{code}' to parent '{parent_code}' "
                "(one of the codes does not exist)."
            )
            continue
        if unit.parent_id != parent.id:
            unit.parent = parent
            unit.save(update_fields=["parent"])

    return {"created": created, "updated": updated, "errors": errors, "total_rows": len(rows)}
