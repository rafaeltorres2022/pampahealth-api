from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.HealthView.as_view()),
    # listas para os filtros
    path("doencas/", views.DoencaListView.as_view()),
    path("hospedeiros/", views.HospedeiroListView.as_view()),
    path("paises/", views.PaisListView.as_view()),
    path("cidades/", views.CidadeListView.as_view()),
    # dados
    path("mapa/", views.MapaView.as_view()),
    path("estatisticas/doencas/", views.EstatisticasDoencasView.as_view()),
    path("estatisticas/crescimento/", views.CrescimentoView.as_view()),
]
