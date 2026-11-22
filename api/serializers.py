from rest_framework import serializers

from .repository import CasoFilters
from .services import GRANULARIDADES


class IdListField(serializers.Field):
    """Aceita IDs inteiros separados por vírgula: ?doenca=1,2,3"""

    default_error_messages = {"invalid": "Use IDs inteiros separados por vírgula (ex.: 1,2,3)."}

    def to_internal_value(self, data):
        try:
            return [int(x) for x in str(data).split(",") if x.strip()]
        except ValueError:
            self.fail("invalid")

    def to_representation(self, value):
        return value


class FiltroSerializer(serializers.Serializer):
    doenca = IdListField(required=False)
    hospedeiro = IdListField(required=False)
    pais = serializers.CharField(required=False, max_length=120)
    cidade = serializers.CharField(required=False, max_length=120)
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)

    def validate(self, attrs):
        inicio, fim = attrs.get("data_inicio"), attrs.get("data_fim")
        if inicio and fim and inicio > fim:
            raise serializers.ValidationError("data_inicio não pode ser posterior a data_fim.")
        return attrs

    def to_filters(self) -> CasoFilters:
        d = self.validated_data
        return CasoFilters(
            doencas=tuple(d.get("doenca", ())),
            hospedeiros=tuple(d.get("hospedeiro", ())),
            pais=d.get("pais"),
            cidade=d.get("cidade"),
            data_inicio=d.get("data_inicio"),
            data_fim=d.get("data_fim"),
        )


class CrescimentoSerializer(FiltroSerializer):
    granularidade = serializers.ChoiceField(choices=GRANULARIDADES, required=False, default="mes")
