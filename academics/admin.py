from django.contrib import admin
from .models import AcademicSession, Programme, Enrollment, Course, CourseRegistration, AttendanceRecord, Exam, ExamResult


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    list_filter = ("is_current",)
    search_fields = ("name",)


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department", "level", "duration_years", "is_active")
    list_filter = ("level", "is_active")
    search_fields = ("name", "code")
    autocomplete_fields = ("department",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "programme", "academic_session", "current_semester", "roll_number", "status")
    list_filter = ("status", "programme", "academic_session")
    search_fields = ("student__username", "student__first_name", "student__last_name", "roll_number")
    autocomplete_fields = ("student", "programme", "academic_session")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "programme", "semester_number", "credits", "course_type", "is_active")
    list_filter = ("course_type", "is_active", "programme")
    search_fields = ("code", "name")
    autocomplete_fields = ("programme",)


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "academic_session", "status")
    list_filter = ("status", "academic_session")
    search_fields = ("student__username", "student__first_name", "student__last_name", "course__code")
    autocomplete_fields = ("student", "course", "academic_session")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("course_registration", "date", "status", "marked_by")
    list_filter = ("status", "date")
    autocomplete_fields = ("course_registration", "marked_by")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("course", "exam_type", "academic_session", "exam_date", "max_marks", "passing_marks", "is_published")
    list_filter = ("exam_type", "is_published", "academic_session")
    search_fields = ("course__code", "course__name")
    autocomplete_fields = ("course", "academic_session")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("exam", "course_registration", "marks_obtained", "is_eligible", "entered_by")
    list_filter = ("is_eligible", "exam")
    autocomplete_fields = ("exam", "course_registration", "entered_by")

