from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .models import AcademicSession, Programme, Enrollment, Course, CourseRegistration, AttendanceRecord
from .forms import AcademicSessionForm, ProgrammeForm, EnrollmentForm, CourseForm, CourseRegistrationForm
from .services import attendance_percentage
from .services import import_enrollments_from_csv, import_enrollments_from_excel


def _is_admin(user):
    from accounts.models import User
    return bool(user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN))


# ---------------- Academic Sessions ----------------

@login_required
def session_list(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    sessions = AcademicSession.objects.all()
    return render(request, "academics/session_list.html", {"sessions": sessions})


@login_required
def session_create(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    form = AcademicSessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"Created session '{obj.name}'.")
        return redirect("session_list")
    return render(request, "academics/session_form.html", {"form": form, "mode": "create"})


@login_required
def session_edit(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(AcademicSession, pk=pk)
    form = AcademicSessionForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated '{target.name}'.")
        return redirect("session_list")
    return render(request, "academics/session_form.html", {"form": form, "mode": "edit", "target": target})


# ---------------- Programmes ----------------

@login_required
def programme_list(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    programmes = Programme.objects.select_related("department")
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        programmes = programmes.filter(Q(name__icontains=q) | Q(code__icontains=q))
    return render(request, "academics/programme_list.html", {"programmes": programmes, "q": q})


@login_required
def programme_create(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    form = ProgrammeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"Created '{obj.name}'.")
        return redirect("programme_list")
    return render(request, "academics/programme_form.html", {"form": form, "mode": "create"})


@login_required
def programme_edit(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(Programme, pk=pk)
    form = ProgrammeForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated '{target.name}'.")
        return redirect("programme_list")
    return render(request, "academics/programme_form.html", {"form": form, "mode": "edit", "target": target})


@login_required
def programme_toggle_active(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied
    target = get_object_or_404(Programme, pk=pk)
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    state = "reactivated" if target.is_active else "deactivated"
    messages.success(request, f"'{target.name}' has been {state}.")
    return redirect("programme_list")


# ---------------- Enrollments ----------------

@login_required
def enrollment_list(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    enrollments = Enrollment.objects.select_related("student", "programme", "academic_session")
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=q) | Q(student__last_name__icontains=q) |
            Q(student__username__icontains=q) | Q(roll_number__icontains=q)
        )
    return render(request, "academics/enrollment_list.html", {"enrollments": enrollments, "q": q})


@login_required
def enrollment_create(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    form = EnrollmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            obj = form.save()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, "academics/enrollment_form.html", {"form": form, "mode": "create"})
        messages.success(request, f"Enrolled {obj.student.get_full_name() or obj.student.username}.")
        return redirect("enrollment_list")
    return render(request, "academics/enrollment_form.html", {"form": form, "mode": "create"})


@login_required
def enrollment_edit(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(Enrollment, pk=pk)
    form = EnrollmentForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, "academics/enrollment_form.html", {"form": form, "mode": "edit", "target": target})
        messages.success(request, f"Updated {target.student.get_full_name() or target.student.username}.")
        return redirect("enrollment_list")
    return render(request, "academics/enrollment_form.html", {"form": form, "mode": "edit", "target": target})


@login_required
def enrollment_import(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    result = None
    if request.method == "POST":
        uploaded = request.FILES.get("file")
        if not uploaded:
            messages.error(request, "Please choose a CSV or Excel file.")
        else:
            try:
                if uploaded.name.lower().endswith(".xlsx"):
                    result = import_enrollments_from_excel(uploaded)
                else:
                    result = import_enrollments_from_csv(uploaded)
                if result["errors"]:
                    messages.warning(request, f"{result['created']} created, {result['updated']} updated, {len(result['errors'])} row problems.")
                else:
                    messages.success(request, f"{result['created']} created, {result['updated']} updated.")
            except ValueError as exc:
                messages.error(request, str(exc))
    return render(request, "academics/enrollment_import.html", {"result": result})


# ---------------- Courses ----------------

@login_required
def course_list(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    courses = Course.objects.select_related("programme")
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        courses = courses.filter(Q(name__icontains=q) | Q(code__icontains=q))
    return render(request, "academics/course_list.html", {"courses": courses, "q": q})


@login_required
def course_create(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    form = CourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"Created '{obj.name}'.")
        return redirect("course_list")
    return render(request, "academics/course_form.html", {"form": form, "mode": "create"})


@login_required
def course_edit(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(Course, pk=pk)
    form = CourseForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated '{target.name}'.")
        return redirect("course_list")
    return render(request, "academics/course_form.html", {"form": form, "mode": "edit", "target": target})


@login_required
def course_toggle_active(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied
    target = get_object_or_404(Course, pk=pk)
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    state = "reactivated" if target.is_active else "deactivated"
    messages.success(request, f"'{target.name}' has been {state}.")
    return redirect("course_list")


@login_required
def registration_list(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    registrations = CourseRegistration.objects.select_related("student", "course", "academic_session")
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        registrations = registrations.filter(
            Q(student__first_name__icontains=q) | Q(student__last_name__icontains=q) |
            Q(student__username__icontains=q) | Q(course__code__icontains=q)
        )
    return render(request, "academics/registration_list.html", {"registrations": registrations, "q": q})


@login_required
def registration_create(request):
    if not _is_admin(request.user):
        raise PermissionDenied
    form = CourseRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            obj = form.save()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, "academics/registration_form.html", {"form": form, "mode": "create"})
        messages.success(request, f"Registered {obj.student.get_full_name() or obj.student.username} for {obj.course.code}.")
        return redirect("registration_list")
    return render(request, "academics/registration_form.html", {"form": form, "mode": "create"})


@login_required
def registration_edit(request, pk):
    if not _is_admin(request.user):
        raise PermissionDenied
    target = get_object_or_404(CourseRegistration, pk=pk)
    form = CourseRegistrationForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, "academics/registration_form.html", {"form": form, "mode": "edit", "target": target})
        messages.success(request, "Updated.")
        return redirect("registration_list")
    return render(request, "academics/registration_form.html", {"form": form, "mode": "edit", "target": target})



# ---------------- Attendance ----------------

def _can_mark_attendance(user):
    """
    Teachers/Staff/HOD can mark attendance for courses taught under
    their own department; Admins/superusers can mark for any course -
    same department-scoping principle used everywhere else in the app.
    """
    from accounts.models import User
    return bool(
        user.is_authenticated and
        (user.is_superuser or user.role in {User.Role.TEACHER, User.Role.HOD, User.Role.STAFF, User.Role.ADMIN})
    )


def _courses_for_attendance(user):
    qs = Course.objects.filter(is_active=True).select_related("programme", "programme__department")
    if user.is_superuser or user.role == "ADMIN":
        return qs
    if getattr(user, "org_unit_id", None):
        return qs.filter(programme__department_id=user.org_unit_id)
    return qs.none()


@login_required
def attendance_course_list(request):
    if not _can_mark_attendance(request.user):
        raise PermissionDenied
    courses = _courses_for_attendance(request.user)
    return render(request, "academics/attendance_course_list.html", {"courses": courses})


@login_required
def attendance_mark(request, course_id):
    if not _can_mark_attendance(request.user):
        raise PermissionDenied
    course = get_object_or_404(_courses_for_attendance(request.user), pk=course_id)

    from datetime import date as date_cls
    date_str = request.GET.get("date") or request.POST.get("date")
    mark_date = date_cls.fromisoformat(date_str) if date_str else date_cls.today()

    registrations = CourseRegistration.objects.filter(
        course=course, status=CourseRegistration.Status.REGISTERED
    ).select_related("student")

    existing = {
        r.course_registration_id: r
        for r in AttendanceRecord.objects.filter(course_registration__course=course, date=mark_date)
    }

    if request.method == "POST":
        for reg in registrations:
            status = request.POST.get(f"status_{reg.id}", AttendanceRecord.Status.PRESENT)
            record, _ = AttendanceRecord.objects.update_or_create(
                course_registration=reg, date=mark_date,
                defaults={"status": status, "marked_by": request.user},
            )
        messages.success(request, f"Attendance saved for {course.code} on {mark_date}.")
        return redirect(f"/academics/attendance/mark/{course.id}/?date={mark_date}")

    rows = [
        {"registration": reg, "current_status": existing[reg.id].status if reg.id in existing else "PRESENT"}
        for reg in registrations
    ]
    return render(request, "academics/attendance_mark.html", {
        "course": course, "date": mark_date, "rows": rows,
    })


@login_required
def attendance_report(request, course_id):
    if not _can_mark_attendance(request.user):
        raise PermissionDenied
    course = get_object_or_404(_courses_for_attendance(request.user), pk=course_id)
    registrations = CourseRegistration.objects.filter(
        course=course, status=CourseRegistration.Status.REGISTERED
    ).select_related("student")
    rows = [
        {"student": reg.student, "percentage": attendance_percentage(reg)}
        for reg in registrations
    ]
    return render(request, "academics/attendance_report.html", {"course": course, "rows": rows})
