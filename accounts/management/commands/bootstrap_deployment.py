import os

from django.core.management.base import BaseCommand
from django.core.management import call_command

from accounts.models import User


class Command(BaseCommand):
    help = (
        "One-time setup for a fresh deployment: creates a superuser from "
        "environment variables (if one doesn't already exist) and loads "
        "the starter org units CSV. Safe to run on every deploy - it "
        "skips anything already done."
    )

    def handle(self, *args, **options):

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

        if username and password:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(
                    username=username, email=email, password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created superuser '{username}'.")
                )
            else:
                self.stdout.write(
                    f"Superuser '{username}' already exists - skipped."
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD "
                    "not set - skipped superuser creation."
                )
            )

        csv_path = "organizations/org_units_starter_template.csv"
        if os.path.exists(csv_path):
            call_command("import_org_units", csv_path)
        else:
            self.stdout.write(
                self.style.WARNING(f"{csv_path} not found - skipped org units import.")
            )
