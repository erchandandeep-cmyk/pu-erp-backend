from django.core.management.base import BaseCommand
from applications.models import ApplicationType

class Command(BaseCommand):
    help = "Create the standard application types."

    def handle(self, *args, **options):
        items = [
            ("Leave Application", "Request leave from the department."),
            ("Bonafide / Certificate Request", "Request a departmental certificate or bonafide."),
            ("NOC Request", "Request a no-objection certificate."),
            ("Document Verification", "Submit documents for departmental verification."),
            ("General Application", "Other departmental requests."),
        ]
        for name, description in items:
            ApplicationType.objects.get_or_create(name=name, defaults={"description": description, "default_authority_role": "HOD", "active": True})
        self.stdout.write(self.style.SUCCESS("Standard application types are ready."))
