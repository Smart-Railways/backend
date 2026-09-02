from rest_framework import serializers

from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
    asset_title = serializers.CharField(source="name")
    category = serializers.CharField(source="asset_type")
    division = serializers.CharField(source="department")
    risk_level = serializers.IntegerField(source="criticality")
    setup_date = serializers.DateField(
        source="installation_date",
        required=False,
        allow_null=True,
    )
    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
    )

    class Meta:
        model = Asset
        fields = [
            "id",
            "asset_title",
            "category",
            "division",
            "risk_level",
            "setup_date",
            "section",
            "section_name",
        ]