from rest_framework import serializers
from accounts.models import User
from applications.models import Application, ApplicationType
from announcements.models import Announcement

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    org_unit_name = serializers.CharField(source="org_unit.name", read_only=True, default=None)
    current_enrollment = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "employee_or_student_id", "phone", "department", "org_unit", "org_unit_name", "semester", "section", "display_name", "current_enrollment"]

    def get_current_enrollment(self, obj):
        active = obj.enrollments.filter(status="ACTIVE").select_related("programme", "academic_session").first() if hasattr(obj, "enrollments") else None
        if not active:
            return None
        return {
            "programme": active.programme.name,
            "programme_code": active.programme.code,
            "academic_session": active.academic_session.name,
            "current_semester": active.current_semester,
            "roll_number": active.roll_number,
        }


class AuthoritySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    org_unit_name = serializers.CharField(source="org_unit.name", read_only=True, default=None)
    class Meta:
        model = User
        fields = ["id", "display_name", "role", "department", "org_unit_name"]

class ApplicationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationType
        fields = ["id", "name", "description", "default_authority_role", "active"]

class ApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source="applicant.display_name", read_only=True)
    application_type_name = serializers.CharField(source="application_type.name", read_only=True)
    class Meta:
        model = Application
        fields = ["id", "application_id", "applicant_name", "application_type", "application_type_name", "subject", "body", "authority", "status", "current_remark", "attachment", "created_at", "updated_at"]
        read_only_fields = ["application_id", "applicant_name", "application_type_name", "status", "current_remark", "created_at", "updated_at"]

class AnnouncementSerializer(serializers.ModelSerializer):
    published_by_name = serializers.CharField(source="published_by.display_name", read_only=True)
    class Meta:
        model = Announcement
        fields = ["id", "title", "body", "audience", "attachment", "published_by", "published_by_name", "published_at", "expires_at", "active"]
        read_only_fields = ["published_by", "published_by_name", "published_at"]
