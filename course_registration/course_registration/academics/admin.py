from django.contrib import admin
from .models import AcademicSession, Programme, Enrollment, Course, CourseRegistration


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

