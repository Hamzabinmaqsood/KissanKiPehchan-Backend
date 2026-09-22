from rest_framework import serializers


class DashboardPayloadSerializer(serializers.Serializer):
    """
    Validates the aggregate JSON object used by the existing
    dashboard.html/editor.html frontend.

    The detailed conversion into relational models is handled
    by services.py.
    """

    brand = serializers.DictField()
    header = serializers.DictField()
    stats = serializers.ListField(
        child=serializers.DictField(),
    )

    partsTitle = serializers.CharField()
    parts = serializers.ListField(
        child=serializers.DictField(),
    )

    overallTitle = serializers.CharField()
    overall = serializers.DictField()

    timelineTitle = serializers.CharField()
    phases = serializers.ListField(
        child=serializers.DictField(),
    )
    nodes = serializers.ListField(
        child=serializers.CharField(),
    )
    legend = serializers.ListField(
        child=serializers.DictField(),
    )

    highlightsTitle = serializers.CharField()
    highlights = serializers.ListField(
        child=serializers.CharField(),
    )

    upcomingTitle = serializers.CharField()
    upcoming = serializers.ListField(
        child=serializers.CharField(),
    )

    weeklyTitle = serializers.CharField()
    weekly = serializers.ListField(
        child=serializers.DictField(),
    )

    riskTitle = serializers.CharField()
    risks = serializers.ListField(
        child=serializers.DictField(),
    )

    snapTitle = serializers.CharField()
    snapshot = serializers.ListField(
        child=serializers.DictField(),
    )

    stakeTitle = serializers.CharField()
    stakeHead = serializers.ListField(
        child=serializers.CharField(),
    )
    stakeholders = serializers.ListField(
        child=serializers.DictField(),
    )

    footer = serializers.ListField(
        child=serializers.DictField(),
    )

    auto = serializers.DictField()

    def validate_parts(
        self,
        value,
    ):
        numbers = []

        for index, part in enumerate(
            value,
            start=1,
        ):
            if not part.get("name"):
                raise serializers.ValidationError(
                    f"Part {index} requires a name."
                )

            number = part.get(
                "num",
                index,
            )

            try:
                number = int(number)
            except (
                TypeError,
                ValueError,
            ):
                raise serializers.ValidationError(
                    f"Part {index} has an invalid number."
                )

            if number in numbers:
                raise serializers.ValidationError(
                    f"Duplicate part number: {number}."
                )

            numbers.append(
                number
            )

        return value

    def validate_weekly(
        self,
        value,
    ):
        weeks = []

        for index, row in enumerate(
            value,
            start=1,
        ):
            week = str(
                row.get(
                    "week",
                    f"W{index}",
                )
            )

            digits = "".join(
                character
                for character in week
                if character.isdigit()
            )

            if not digits:
                raise serializers.ValidationError(
                    f"Weekly row {index} has an invalid week."
                )

            week_number = int(
                digits
            )

            if week_number in weeks:
                raise serializers.ValidationError(
                    f"Duplicate week: W{week_number}."
                )

            weeks.append(
                week_number
            )

        return value

    def validate_auto(
        self,
        value,
    ):
        start = value.get(
            "startDate"
        )
        end = value.get(
            "endDate"
        )

        if start and end:
            try:
                from datetime import date

                start_date = (
                    date.fromisoformat(
                        start
                    )
                )

                end_date = (
                    date.fromisoformat(
                        end
                    )
                )

            except ValueError:
                raise serializers.ValidationError(
                    "startDate and endDate must use YYYY-MM-DD."
                )

            if end_date < start_date:
                raise serializers.ValidationError(
                    "Project endDate cannot be before startDate."
                )

        return value
