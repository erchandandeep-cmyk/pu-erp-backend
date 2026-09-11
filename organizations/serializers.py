from rest_framework import serializers

from .models import OrgUnit


class OrgUnitSerializer(serializers.ModelSerializer):
    unit_type_display = serializers.CharField(source="get_unit_type_display", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)

    class Meta:
        model = OrgUnit
        fields = [
            "id",
            "code",
            "name",
            "unit_type",
            "unit_type_display",
            "parent",
            "parent_name",
        ]
