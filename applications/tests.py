from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import ApplicationType, Application

class ApplicationFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student", password="StrongPass123!",
            employee_or_student_id="TESTSTU1", role=User.Role.STUDENT
        )
        self.hod = User.objects.create_user(
            username="hod", password="StrongPass123!",
            employee_or_student_id="TESTHOD1", role=User.Role.HOD
        )
        self.app_type = ApplicationType.objects.create(
            name="NOC Request", default_authority_role="HOD"
        )

    def test_student_can_login_and_create_application(self):
        self.client.login(username="student", password="StrongPass123!")
        response = self.client.post(reverse("create_application"), {
            "application_type": self.app_type.pk,
            "subject": "Test NOC",
            "body": "Please process this request.",
            "authority": self.hod.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(Application.objects.first().applicant, self.student)

    def test_hod_can_approve(self):
        app = Application.objects.create(
            applicant=self.student,
            application_type=self.app_type,
            subject="Test NOC",
            body="Please process this request.",
            authority=self.hod,
        )
        self.client.login(username="hod", password="StrongPass123!")
        response = self.client.post(reverse("application_action", args=[app.pk, "approve"]), {"remark": "Approved for demo."})
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.APPROVED)
