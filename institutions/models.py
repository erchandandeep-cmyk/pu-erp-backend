from django.db import models


class Institution(models.Model):
    """
    A single node in the university's organisational tree.

    This one model represents every kind of unit the university has —
    the university itself, its regional centres, constituent colleges,
    neighbourhood campuses, affiliated colleges elsewhere in the state,
    and the departments/offices inside any of them. Departments no
    longer have to live only under "the university" directly — a
    department can belong to a constituent college, a regional centre,
    or the main campus, exactly like the real institution does.

    Because it is a self-referencing tree, growing from one department
    (Mechanical Engineering) to the entire university (70+ departments,
    5+ regional centres, 10+ constituent colleges, 10+ neighbourhood
    campuses, 200+ affiliated colleges) never requires new code or a
    new migration — new rows are simply added, normally from the
    Django admin site, under Institutions.
    """

    class Kind(models.TextChoices):
        UNIVERSITY = "UNIVERSITY", "University"
        REGIONAL_CENTRE = "REGIONAL_CENTRE", "Regional Centre"
        CONSTITUENT_COLLEGE = "CONSTITUENT_COLLEGE", "Constituent College"
        NEIGHBOURHOOD_CAMPUS = "NEIGHBOURHOOD_CAMPUS", "Neighbourhood Campus"
        AFFILIATED_COLLEGE = "AFFILIATED_COLLEGE", "Affiliated College"
        DEPARTMENT = "DEPARTMENT", "Department / Office"

    name = models.CharField(
        max_length=200,
        help_text="e.g. 'Mechanical Engineering', 'Guru Kashi Campus', 'Punjabi University, Patiala'",
    )
    code = models.SlugField(
        max_length=20,
        unique=True,
        help_text="Short unique code used in IDs, e.g. MECH, CSE, GKC, RC-BTI.",
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="What this belongs under. Leave blank only for the university root.",
    )
    city = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "name"]
        indexes = [
            models.Index(fields=["kind"]),
            models.Index(fields=["parent"]),
        ]
        verbose_name = "Institution / Unit"
        verbose_name_plural = "Institutions / Units"

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"

    def full_path(self):
        """Human readable breadcrumb, e.g. 'Punjabi University → Guru Kashi Campus → CSE'."""
        parts = [self.name]
        node = self.parent
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return " -> ".join(reversed(parts))

    def get_university_root(self):
        node = self
        while node.parent is not None:
            node = node.parent
        return node
