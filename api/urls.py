from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from . import views

urlpatterns = [
    path("health/", views.HealthView.as_view()),
    # listas para os filtros
    path("doencas/", views.DoencaListView.as_view()),
    path("doencas/<int:doenca_id>/fontes/", views.DoencaFontesView.as_view()),
    path("hospedeiros/", views.HospedeiroListView.as_view()),
    path("paises/", views.PaisListView.as_view()),
    path("cidades/", views.CidadeListView.as_view()),
    # dados
    path("mapa/", views.MapaView.as_view()),
    path("fontes/", views.FontesView.as_view()),
    path("estatisticas/doencas/", views.EstatisticasDoencasView.as_view()),
    path("estatisticas/crescimento/", views.CrescimentoView.as_view()),
    # Gera o arquivo schema.yml automaticamente
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Interface visual do Swagger que consome o schema
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
