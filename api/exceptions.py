import logging

import httpx
from postgrest.exceptions import APIError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def handler(exc, context):
    """Erros do DRF seguem o padrão; falhas do Supabase viram 502 sem vazar detalhes."""
    response = exception_handler(exc, context)
    if response is not None:
        return response
    if isinstance(exc, (APIError, httpx.HTTPError)):
        logger.exception("Falha ao consultar o Supabase")
        return Response({"detail": "Falha ao consultar a base de dados."}, status=502)
    return None
