from django.core.management.base import BaseCommand, CommandError

from organizations.models import OrgUnit
from organizations.services import import_org_units_from_csv

VALID_TYPES = {c[0] for c in OrgUnit.UnitType.choices}


class Command(BaseCommand):
    help = (
        "Bulk import/update Organisation Units (departments, centres, "
        "colleges, offices) from a CSV file.\n"
        "Required columns: code,name,unit_type\n"
        "Optional columns: parent_code,contact_email,contact_phone,address\n"
        f"Allowed unit_type values: {', '.join(sorted(VALID_TYPES))}\n"
        "Run twice with the same file safely - existing codes are updated, "
        "not duplicated."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    def handle(self, *args, **options):
        path = options["csv_path"]
        try:
            f = open(path, "rb")
        except OSError as exc:
            raise CommandError(f"Could not open '{path}': {exc}")

        with f:
            try:
                result = import_org_units_from_csv(f)
            except ValueError as exc:
                raise CommandError(str(exc))

        if result["errors"]:
            self.stdout.write(self.style.WARNING(f"{len(result['errors'])} row(s) had problems:"))
            for e in result["errors"]:
                self.stdout.write(self.style.WARNING(f"  - {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"Done. Created {result['created']}, updated {result['updated']} org unit(s).")
        )
