from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from institutions.models import Institution


class Command(BaseCommand):
    """
    Run this ONCE, right after `migrate`, when upgrading an existing
    ME-ERP install to the university-wide data model.

    What it does:
      1. Creates the university root node (if it does not exist yet).
      2. Creates a Department node for every distinct value currently
         stored in accounts.User.department (so "Mechanical
         Engineering" and any other value already in your data gets
         its own row), parented under the university root.
      3. Points every existing user's new `institution` field at the
         matching department node, based on their current department
         text. Nothing in the old `department` text field is deleted
         or changed — this is purely additive.

    Safe to re-run: it will not create duplicates or touch users that
    already have an institution set.
    """

    help = "Seed the university institution tree and backfill existing users (safe to re-run)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--university-name",
            default="Punjabi University, Patiala",
            help="Name of the university root node.",
        )
        parser.add_argument(
            "--university-code",
            default="PUP",
            help="Short code for the university root node.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from accounts.models import User

        university, created = Institution.objects.get_or_create(
            code=options["university_code"],
            defaults={
                "name": options["university_name"],
                "kind": Institution.Kind.UNIVERSITY,
                "parent": None,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created university root: {university}"))
        else:
            self.stdout.write(f"University root already exists: {university}")

        department_names = (
            User.objects.exclude(department="")
            .exclude(department__isnull=True)
            .values_list("department", flat=True)
            .distinct()
        )

        dept_lookup = {}
        for dept_name in department_names:
            dept_name = dept_name.strip()
            if not dept_name:
                continue
            code = slugify(dept_name)[:20] or "dept"
            base_code = code
            suffix = 1
            # Guarantee a unique code even if two department names slugify the same.
            while (
                Institution.objects.filter(code=code)
                .exclude(name=dept_name)
                .exists()
            ):
                suffix += 1
                code = f"{base_code[:17]}-{suffix}"

            dept, dept_created = Institution.objects.get_or_create(
                name=dept_name,
                kind=Institution.Kind.DEPARTMENT,
                parent=university,
                defaults={"code": code},
            )
            dept_lookup[dept_name] = dept
            if dept_created:
                self.stdout.write(self.style.SUCCESS(f"Created department: {dept}"))

        updated = 0
        for user in User.objects.filter(institution__isnull=True).exclude(department=""):
            dept = dept_lookup.get(user.department.strip())
            if dept is not None:
                user.institution = dept
                user.save(update_fields=["institution"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Linked {updated} existing users to their department."))
        self.stdout.write(
            self.style.SUCCESS(
                "Done. Add regional centres, constituent colleges, neighbourhood campuses, "
                "affiliated colleges and further departments any time from /admin/ under "
                "'University Structure -> Institutions / Units'."
            )
        )
