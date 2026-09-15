from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .models import AcademicSession, Programme, Enrollment, Course, CourseRegistration, AttendanceRecord, Exam, ExamResult
from .forms import AcademicSessionForm, ProgrammeForm, EnrollmentForm, CourseForm, CourseRegistrationForm, ExamForm
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


# ---------------- Examinations ----------------

@login_required
def exam_list(request):
    if not _can_mark_attendance(request.user):  # same role gate as attendance
        raise PermissionDenied
    courses = _courses_for_attendance(request.user)
    exams = Exam.objects.filter(course__in=courses).select_related("course", "academic_session")
    return render(request, "academics/exam_list.html", {"exams": exams})


@login_required
def exam_create(request):
    if not _can_mark_attendance(request.user):
        raise PermissionDenied
    form = ExamForm(request.POST or None)
    form.fields["course"].queryset = _courses_for_attendance(request.user)
    if request.method == "POST" and form.is_valid():
        try:
            obj = form.save()
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, "academics/exam_form.html", {"form": form, "mode": "create"})
        messages.success(request, f"Created exam '{obj}'.")
        return redirect("exam_list")
    return render(request, "academics/exam_form.html", {"form": form, "mode": "create"})


@login_required
def exam_edit(request, pk):
    if not _can_mark_attendance(request.user):
        raise PermissionDenied
    target = get_object_or_404(Exam, pk=pk, course__in=_courses_for_attendance(request.user))
    form = ExamForm(request.POST or None, instance=target)
    form.fields["course"].queryset = _courses_for_attendance(request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Updated.")
        return redirect("exam_list")
    return render(request, "academics/exam_form.html", {"form": form, "mode": "edit", "target": target})


@login_required
def exam_toggle_publish(request, pk):
    if not _can_mark_attendance(request.user):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied
    target = get_object_or_404(Exam, pk=pk, course__in=_courses_for_attendance(request.user))
    target.is_published = not target.is_published
    target.save(update_fields=["is_published"])
    state = "published - students can now see their marks" if target.is_published else "unpublished"
    messages.success(request, f"'{target}' has been {state}.")
    return redirect("exam_list")


@login_required
def marks_entry(request, exam_id):
    if not _can_mark_attendance(request.user):
        raise PermissionDenied
    exam = get_object_or_404(Exam, pk=exam_id, course__in=_courses_for_attendance(request.user))
    registrations = CourseRegistration.objects.filter(
        course=exam.course, status=CourseRegistration.Status.REGISTERED
    ).select_related("student")

    existing = {r.course_registration_id: r for r in ExamResult.objects.filter(exam=exam)}

    if request.method == "POST":
        for reg in registrations:
            raw_marks = request.POST.get(f"marks_{reg.id}", "").strip()
            pct = attendance_percentage(reg)
            is_eligible = pct is None or pct >= exam.min_attendance_percent
            marks_value = None
            if raw_marks:
                try:
                    marks_value = float(raw_marks)
                except ValueError:
                    messages.error(request, f"'{raw_marks}' is not a valid number for {reg.student}.")
                    continue
            result, _ = ExamResult.objects.update_or_create(
                exam=exam, course_registration=reg,
                defaults={
                    "marks_obtained": marks_value,
                    "is_eligible": is_eligible,
                    "attendance_percent_snapshot": pct,
                    "entered_by": request.user,
                },
            )
            try:
                result.full_clean()
            except Exception as exc:
                messages.error(request, f"{reg.student}: {exc}")
        messages.success(request, f"Marks saved for {exam}.")
        return redirect("marks_entry", exam_id=exam.id)

    rows = []
    for reg in registrations:
        pct = attendance_percentage(reg)
        prior = existing.get(reg.id)
        rows.append({
            "registration": reg,
            "attendance_percent": pct,
            "eligible": pct is None or pct >= exam.min_attendance_percent,
            "current_marks": prior.marks_obtained if prior else "",
        })
    return render(request, "academics/marks_entry.html", {"exam": exam, "rows": rows})


# ---------------- Transcript / Results ----------------

def _build_transcript(student):
    """
    Every enrollment the student has, and for each course they've
    registered for under it, every PUBLISHED exam result. Unpublished
    exams never appear here, regardless of who's viewing - marks
    aren't official until a teacher/admin explicitly publishes them.
    """
    enrollments = Enrollment.objects.filter(student=student).select_related("programme", "academic_session")
    data = []
    for enrollment in enrollments:
        registrations = CourseRegistration.objects.filter(
            student=student, course__programme=enrollment.programme
        ).select_related("course")
        courses = []
        for reg in registrations:
            results = ExamResult.objects.filter(
                course_registration=reg, exam__is_published=True
            ).select_related("exam")
            if not results.exists():
                continue
            courses.append({
                "course": reg.course,
                "results": [
                    {
                        "exam": r.exam,
                        "marks_obtained": r.marks_obtained,
                        "percentage": r.percentage,
                        "passed": r.passed,
                        "is_eligible": r.is_eligible,
                    }
                    for r in results
                ],
            })
        if courses:
            data.append({"enrollment": enrollment, "courses": courses})
    return data


@login_required
def my_transcript(request):
    from accounts.models import User
    if request.user.role != User.Role.STUDENT:
        raise PermissionDenied("Only students have a transcript to view here.")
    return render(request, "academics/transcript.html", {
        "student": request.user, "transcript": _build_transcript(request.user), "is_self": True,
    })


@login_required
def student_transcript(request, student_id):
    """
    Staff view of a specific student's transcript, scoped the same way
    as everything else - same department, or Admin/superuser for
    university-wide access.
    """
    from accounts.models import User
    if not (request.user.is_superuser or request.user.role in {User.Role.TEACHER, User.Role.HOD, User.Role.STAFF, User.Role.ADMIN}):
        raise PermissionDenied
    student = get_object_or_404(User, pk=student_id, role=User.Role.STUDENT)
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
        if not request.user.org_unit_id or request.user.org_unit_id != student.org_unit_id:
            raise PermissionDenied("You can only view transcripts for students in your own department.")
    return render(request, "academics/transcript.html", {
        "student": student, "transcript": _build_transcript(student), "is_self": False,
    })
