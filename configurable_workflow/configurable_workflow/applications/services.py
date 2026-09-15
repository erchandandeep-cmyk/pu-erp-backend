from organizations.models import OrgUnit


def suggest_authority(applicant, application_type):
    """
    Implements the 'workflow should be configurable, not hard-coded'
    principle: each ApplicationType has a `default_authority_role`
    (e.g. HOD) and a `route_to_admin_office` flag, both editable by an
    admin with no code changes. Given who's applying and what type of
    application it is, this returns the single best-matching person to
    default the 'send to' field to - or None if nobody matches (the
    picker then falls back to showing every option unfiltered).

    This never removes the ability to pick someone else manually - it
    only supplies a sensible starting point.
    """

    from accounts.models import User  # local import avoids a circular import

    if application_type is None:
        return None

    qs = User.objects.filter(
        role=application_type.default_authority_role,
        is_active=True,
        is_active_account=True,
    )

    if application_type.route_to_admin_office:
        admin_office_ids = OrgUnit.objects.filter(
            unit_type=OrgUnit.UnitType.ADMIN_OFFICE, is_active=True
        ).values_list("id", flat=True)
        qs = qs.filter(org_unit_id__in=admin_office_ids)
    elif getattr(applicant, "org_unit_id", None):
        qs = qs.filter(org_unit_id=applicant.org_unit_id)
    else:
        return None

    return qs.order_by("first_name", "last_name").first()
