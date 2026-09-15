from django.core.management.base import BaseCommand
from applications.models import ApplicationType


class Command(BaseCommand):
    help = "Create/update the standard set of application types used across the university."

    def handle(self, *args, **options):
        # (name, description, default_authority_role, route_to_admin_office)
        #
        # route_to_admin_office=True means "always goes to a university-wide
        # office (Registrar/Exam Branch/etc.), regardless of which
        # department the applicant is in" - False means "stays within the
        # applicant's own department by default."
        items = [
            # --- Department-level (stays within own department) ---
            ("Leave Application", "Request leave (medical, casual, on-duty, etc.) from the department.", "HOD", False),
            ("Duty Leave / On-Duty Request", "Request approval to attend a conference, event, or official duty.", "HOD", False),
            ("Attendance Shortage Condonation", "Request condonation of attendance shortage below the minimum required.", "HOD", False),
            ("Re-evaluation / Revaluation Request", "Request re-checking of an exam answer sheet.", "HOD", False),
            ("Lab / Equipment Access Request", "Request access to a department lab, workshop, or equipment.", "HOD", False),
            ("Internal Assessment Grievance", "Raise a concern about internal assessment / internal marks.", "TEACHER", False),
            ("Project / Thesis Guide Change Request", "Request a change of project or thesis supervisor.", "HOD", False),

            # --- Registrar's office (university-wide) ---
            ("Bonafide Certificate", "Request an official bonafide student certificate.", "STAFF", True),
            ("Character Certificate", "Request an official character/conduct certificate.", "STAFF", True),
            ("Migration Certificate", "Request a migration certificate (for transfer to another university).", "STAFF", True),
            ("Transfer Certificate", "Request a transfer certificate.", "STAFF", True),
            ("Name / Details Correction Request", "Request correction of name, date of birth, or other official record details.", "STAFF", True),
            ("Gap Year Certificate", "Request a certificate explaining a gap in academic years.", "STAFF", True),
            ("NOC (No Objection Certificate)", "Request a no-objection certificate (e.g. for a job, another course, or visa).", "STAFF", True),
            ("Duplicate ID Card Request", "Request a reissued student/staff ID card.", "STAFF", True),
            ("Address Change Request", "Update the official address on record.", "STAFF", True),

            # --- Examination Branch ---
            ("Transcript Request", "Request an official academic transcript.", "STAFF", True),
            ("Duplicate Marksheet / Degree Request", "Request a duplicate marksheet or degree certificate.", "STAFF", True),
            ("Supplementary / Backlog Exam Form", "Apply to appear for a supplementary or backlog examination.", "STAFF", True),
            ("Exam Form Correction Request", "Request correction of details submitted on an exam form.", "STAFF", True),

            # --- Finance / Accounts ---
            ("Fee Refund Request", "Request a refund of fees paid.", "STAFF", True),
            ("Fee Concession / Waiver Request", "Request a concession or waiver on fees.", "STAFF", True),
            ("Scholarship Application", "Apply for a scholarship or financial aid scheme.", "STAFF", True),
            ("Fee Installment Request", "Request to pay fees in installments.", "STAFF", True),

            # --- Hostel & campus life ---
            ("Hostel Allotment Request", "Apply for a hostel room allotment.", "STAFF", True),
            ("Hostel Room Change Request", "Request a change of hostel room or roommate.", "STAFF", True),
            ("Hostel Leave / Late-Entry Permission", "Request permission for late entry or overnight leave from the hostel.", "STAFF", True),

            # --- Library ---
            ("Library Card Request", "Request issuance of a library card.", "STAFF", True),
            ("Library Fine Waiver Request", "Request a waiver of a library fine.", "STAFF", True),

            # --- Generic catch-all ---
            ("General Application", "Any request that doesn't fit a specific category above.", "HOD", False),
        ]

        created, updated = 0, 0
        for name, description, role, route_admin in items:
            obj, was_created = ApplicationType.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "default_authority_role": role,
                    "route_to_admin_office": route_admin,
                    "active": True,
                },
            )
            created += was_created
            updated += not was_created

        # Clean up old-named duplicates left over from an earlier, shorter
        # version of this list, now that a clearer-named replacement
        # exists. Only deletes if nothing has actually used the old type
        # yet (ApplicationType is PROTECTed - if a real application
        # already used it, Django refuses the delete and we deactivate
        # it instead, so no application history is ever lost silently).
        renamed = {
            "Bonafide / Certificate Request": "Bonafide Certificate",
            "NOC Request": "NOC (No Objection Certificate)",
        }
        cleaned = 0
        for old_name in renamed:
            old = ApplicationType.objects.filter(name=old_name).first()
            if old is None:
                continue
            try:
                old.delete()
                cleaned += 1
            except Exception:
                old.active = False
                old.description = f"(Superseded by '{renamed[old_name]}' - kept inactive since it has application history.)"
                old.save(update_fields=["active", "description"])
                cleaned += 1

        self.stdout.write(self.style.SUCCESS(
            f"Application types ready: {created} created, {updated} updated, "
            f"{cleaned} old duplicate(s) cleaned up ({len(items)} total types)."
        ))
