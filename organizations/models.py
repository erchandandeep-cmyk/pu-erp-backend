from django.db import models


class OrgUnit(models.Model):
    """
    One generic model for every kind of unit in the university:
    teaching departments, research centres, regional centres,
    constituent colleges, neighbourhood campuses, affiliated colleges,
    and non-teaching / administrative offices (VC, Registrar, Deans, etc.).

    Growing from 1 department to 70 departments + 200 colleges is a
    data-entry task (add rows here, or bulk-import a CSV) - it never
    requires touching Python code again.
    """

    class UnitType(models.TextChoices):
        TEACHING_DEPT = "TEACHING_DEPT", "Teaching Department"
        RESEARCH_CENTRE = "RESEARCH_CENTRE", "Research Centre"
        REGIONAL_CENTRE = "REGIONAL_CENTRE", "Regional Centre"
        CONSTITUENT_COLLEGE = "CONSTITUENT_COLLEGE", "Constituent College"
        NEIGHBOURHOOD_CAMPUS = "NEIGHBOURHOOD_CAMPUS", "Neighbourhood Campus"
        AFFILIATED_COLLEGE = "AFFILIATED_COLLEGE", "Affiliated College"
        ADMIN_OFFICE = "ADMIN_OFFICE", "Administrative / Non-Teaching Office"

    code = models.SlugField(
        max_length=30,
        unique=True,
        help_text="Short unique code, e.g. MECH, VC, REG, RC-BATHINDA",
    )
    name = models.CharField(max_length=200)
    unit_type = models.CharField(max_length=30, choices=UnitType.choices)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="e.g. a department's parent could be its Regional Centre; "
        "an office's parent could be the Vice-Chancellor's office.",
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["unit_type", "name"]
        verbose_name = "Organisation Unit"
        verbose_name_plural = "Organisation Units"

    def __str__(self):
        return f"{self.name} ({self.get_unit_type_display()})"
