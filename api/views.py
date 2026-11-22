from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView

from . import repository, services
from .serializers import CrescimentoSerializer, FiltroSerializer


def _cached(key: str, loader):
    """Cache curto para as listas de filtros (mudam raramente)."""
    return cache.get_or_set(f"{settings.APP_ENV}:{key}", loader, settings.LOOKUP_CACHE_SECONDS)


class ReadOnlyView(APIView):
    """Base de todas as views: somente GET/HEAD/OPTIONS."""

    http_method_names = ["get", "head", "options"]


# --------------------------------------------------------------------------
# Infra
# --------------------------------------------------------------------------
class HealthView(ReadOnlyView):
    def get(self, request):
        return Response({"status": "ok", "ambiente": settings.APP_ENV})


# --------------------------------------------------------------------------
# Listas para os filtros
# --------------------------------------------------------------------------
class DoencaListView(ReadOnlyView):
    def get(self, request):
        return Response(_cached("doencas", repository.list_doencas))


class HospedeiroListView(ReadOnlyView):
    def get(self, request):
        return Response(_cached("hospedeiros", repository.list_hospedeiros))


class PaisListView(ReadOnlyView):
    def get(self, request):
        locais = _cached("locais", repository.list_locais)
        return Response(sorted({l["pais"] for l in locais if l["pais"]}))


class CidadeListView(ReadOnlyView):
    def get(self, request):
        pais = request.query_params.get("pais")
        locais = _cached("locais", repository.list_locais)
        cidades = {l["cidade"] for l in locais if l["cidade"] and (not pais or l["pais"] == pais)}
        return Response(sorted(cidades))


# --------------------------------------------------------------------------
# Dados
# --------------------------------------------------------------------------
class FilteredView(ReadOnlyView):
    serializer_class = FiltroSerializer

    def parse_params(self, request):
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer


class MapaView(FilteredView):
    """Bolhas do mapa: ocorrências e mortes por local, detalhadas por doença."""

    def get(self, request):
        filters = self.parse_params(request).to_filters()
        rows = repository.fetch_casos(filters)
        return Response({"total": services.summarize(rows), "locais": services.map_bubbles(rows)})


class EstatisticasDoencasView(FilteredView):
    """Ocorrências e mortes totais por doença."""

    def get(self, request):
        filters = self.parse_params(request).to_filters()
        rows = repository.fetch_casos(filters)
        return Response({"total": services.summarize(rows), "doencas": services.by_disease(rows)})


class CrescimentoView(FilteredView):
    """Crescimento do período escolhido vs. período anterior de mesma duração."""

    serializer_class = CrescimentoSerializer

    def get(self, request):
        serializer = self.parse_params(request)
        filters = serializer.to_filters()
        inicio, fim = services.resolve_period(filters.data_inicio, filters.data_fim)
        ant_inicio, _ = services.previous_period(inicio, fim)

        # Uma única consulta cobrindo o período atual + o anterior.
        rows = repository.fetch_casos(
            repository.CasoFilters(
                doencas=filters.doencas,
                hospedeiros=filters.hospedeiros,
                pais=filters.pais,
                cidade=filters.cidade,
                data_inicio=ant_inicio,
                data_fim=fim,
            )
        )
        return Response(
            services.growth_report(rows, inicio, fim, serializer.validated_data["granularidade"])
        )
