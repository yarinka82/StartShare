from rest_framework import serializers


class IntroductionDecisionSerializer(serializers.Serializer):
    interested = serializers.BooleanField()
    investor_message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )
    decline_reason_code = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    def validate(self, attrs):
        interested = attrs["interested"]
        reason_code = attrs.get("decline_reason_code")

        if interested and reason_code:
            raise serializers.ValidationError({
                "decline_reason_code":
                    "Для відповіді «Цікаво» причину відмови вказувати не потрібно."
            })

        if not interested and not reason_code:
            raise serializers.ValidationError({
                "decline_reason_code":
                    "Для відповіді «Ні» потрібно вказати причину."
            })

        return attrs


class CriterionSuggestionDecisionSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
