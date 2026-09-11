import csv

from django.core.management.base import BaseCommand, CommandError

from organizations.models import OrgUnit

VALID_TYPES = {c[0] for c in OrgUnit.UnitType.choices}


class Command(BaseCommand):
    help = (
        "Bulk import/update Organisation Units (departments, centres, "
        "colleges, offices) from a CSV file.\n"
        "Required columns: code,name,unit_type\n"
        "Optional columns: parent_code,contact_email,contact_phone,address\n"
        f"Allowed unit_type values: {', '.join(sorted(VALID_TYPES))}\n"
        "Run twice with the same file safely - existing codes are updated, "
        "not duplicated. Import parents (offices, centres, colleges) "
        "before the departments/units that reference them as parent_code."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and print what would happen, without saving.",
        )

    def handle(self, *args, **options):
        path = options["csv_path"]
        dry_run = options["dry_run"]

        try:
            f = open(path, newline="", encoding="utf-8-sig")
        except OSError as exc:
            raise CommandError(f"Could not open '{path}': {exc}")

        created, updated, errors = 0, 0, []

        with f:
            reader = csv.DictReader(f)
            required = {"code", "name", "unit_type"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"CSV is missing required column(s): {', '.join(missing)}")

            rows = list(reader)

            # Two passes: create/update units first without parent linking,
            # then link parents - so row order in the CSV does not matter.
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

                if dry_run:
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

            if not dry_run:
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

        if errors:
            self.stdout.write(self.style.WARNING(f"{len(errors)} row(s) had problems:"))
            for e in errors:
                self.stdout.write(self.style.WARNING(f"  - {e}"))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run OK. {len(rows)} row(s) validated."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Done. Created {created}, updated {updated} org unit(s).")
            )
