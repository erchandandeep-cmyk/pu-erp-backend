from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime

from accounts.models import User
from organizations.models import OrgUnit
from academics.models import AcademicSession, Programme, Enrollment, Course, CourseRegistration
from applications.models import ApplicationType


TEST_PASSWORD = "TestPass123"


class Command(BaseCommand):
    help = (
        "Creates one test account for every role (Student, Teacher, HOD, "
        "Admin/Registrar) with a known password, plus a sample programme, "
        "course, enrollment, and course registration - so every module "
        "can be explored end-to-end immediately. Safe to run more than "
        "once (updates instead of duplicating). NEVER use these accounts "
        "or this password for real people - this is exploration/testing "
        "data only."
    )

    def handle(self, *args, **options):
        mech = OrgUnit.objects.filter(unit_type=OrgUnit.UnitType.TEACHING_DEPT).first()
        if mech is None:
            self.stdout.write(self.style.ERROR(
                "No teaching department found - run 'import_org_units' with the "
                "starter CSV first."
            ))
            return

        registrar_office = OrgUnit.objects.filter(name__icontains="Registrar").first()

        def upsert_user(username, role, first, last, org_unit, designation=""):
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "role": role,
                    "first_name": first,
                    "last_name": last,
                    "org_unit": org_unit,
                    "designation": designation,
                    "is_active": True,
                    "is_active_account": True,
                },
            )
            user.set_password(TEST_PASSWORD)
            user.save()
            return user

        student = upsert_user("test_student", User.Role.STUDENT, "Test", "Student", mech)
        teacher = upsert_user("test_teacher", User.Role.TEACHER, "Test", "Teacher", mech, "Assistant Professor")
        hod = upsert_user("test_hod", User.Role.HOD, "Test", "HOD", mech, "Head of Department")
        registrar = upsert_user(
            "test_registrar", User.Role.ADMIN, "Test", "Registrar",
            registrar_office or mech, "Registrar"
        )

        vc_office = OrgUnit.objects.filter(name__icontains="Vice-Chancellor").first()
        dean_academic_office = OrgUnit.objects.filter(name__icontains="Dean, Academic Affairs").first()
        dean_colleges_office = OrgUnit.objects.filter(name__icontains="Dean, College Development Council").first()

        vc = upsert_user("test_vc", User.Role.ADMIN, "Test", "ViceChancellor", vc_office or mech, "Vice-Chancellor")
        dean_academic = upsert_user(
            "test_dean_academic", User.Role.ADMIN, "Test", "DeanAcademic",
            dean_academic_office or vc_office or mech, "Dean, Academic Affairs"
        )
        dean_colleges = upsert_user(
            "test_dean_colleges", User.Role.ADMIN, "Test", "DeanColleges",
            dean_colleges_office or vc_office or mech, "Dean, College Development Council"
        )

        session, _ = AcademicSession.objects.update_or_create(
            name="2026-27",
            defaults={
                "start_date": datetime.date(2026, 7, 1),
                "end_date": datetime.date(2027, 6, 30),
                "is_current": True,
            },
        )

        programme, _ = Programme.objects.update_or_create(
            code="TEST-PROG",
            defaults={
                "name": f"Test Programme ({mech.name})",
                "department": mech,
                "level": Programme.Level.UG,
                "duration_years": 4,
                "total_semesters": 8,
                "is_active": True,
            },
        )

        Enrollment.objects.filter(student=student).exclude(programme=programme).delete()
        Enrollment.objects.update_or_create(
            student=student, programme=programme, academic_session=session,
            defaults={"batch_year": 2026, "roll_number": "TEST001", "current_semester": 1, "status": "ACTIVE"},
        )

        course, _ = Course.objects.update_or_create(
            code="TEST101",
            defaults={
                "name": "Test Course",
                "programme": programme,
                "semester_number": 1,
                "credits": 4,
                "course_type": Course.CourseType.CORE,
                "is_active": True,
            },
        )

        CourseRegistration.objects.update_or_create(
            student=student, course=course, academic_session=session,
            defaults={"status": "REGISTERED"},
        )

        apptype = ApplicationType.objects.first()
        if apptype:
            apptype.default_authority_role = "HOD"
            apptype.route_to_admin_office = False
            apptype.save()

        self.stdout.write(self.style.SUCCESS(
            "\nTest accounts ready - password for ALL of them: " + TEST_PASSWORD + "\n"
            "  test_student        (Student, enrolled in Test Programme, registered for TEST101)\n"
            "  test_teacher        (Teacher, same department as test_student)\n"
            "  test_hod            (HOD, same department as test_teacher - receives their applications)\n"
            "  test_registrar      (Admin, Registrar's office)\n"
            "  test_vc             (Admin, Vice-Chancellor's office)\n"
            "  test_dean_academic  (Admin, Dean Academic Affairs office)\n"
            "  test_dean_colleges  (Admin, Dean College Development Council office)\n"
        ))
