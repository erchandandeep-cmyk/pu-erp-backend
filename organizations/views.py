from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import OrgUnit
from .serializers import OrgUnitSerializer


class OrgUnitViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only list of active org units, so the login/registration
    screen (web or mobile) can show a department/college dropdown before
    the user is authenticated.
    """

    queryset = OrgUnit.objects.filter(is_active=True).select_related("parent")
    serializer_class = OrgUnitSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["unit_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        unit_type = self.request.query_params.get("unit_type")
        if unit_type:
            qs = qs.filter(unit_type=unit_type.upper())
        return qs.order_by("unit_type", "name")
