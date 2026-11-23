"""Acesso somente leitura ao Supabase (PostgREST).

Só existem operações de SELECT aqui; nenhum insert/update/delete.
Os nomes das tabelas seguem o diagrama do banco (pampahealth schema v1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from .supabase_client import get_client

T_CASOS = "casos_identificados"
T_ZOONOSES = "zoonoses"
T_HOSPEDEIROS = "especies_hospedeiro"
T_ZOONOSE_HOSPEDEIRO = "zoonose_hospedeiro"
T_LOCAIS = "locais"
T_FONTES = "fontes"

PAGE_SIZE = 1000  # limite padrão do PostgREST por requisição


@dataclass(frozen=True)
class CasoFilters:
    doencas: tuple[int, ...] = ()
    hospedeiros: tuple[int, ...] = ()
    pais: str | None = None
    cidade: str | None = None
    data_inicio: date | None = None  # filtra por fontes.data_publicacao
    data_fim: date | None = None


def _fetch_all(build_query: Callable) -> list[dict]:
    """Percorre todas as páginas de uma consulta (a query é recriada a cada página)."""
    rows: list[dict] = []
    offset = 0
    while True:
        batch = build_query().range(offset, offset + PAGE_SIZE - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


# --------------------------------------------------------------------------
# Listas para os filtros do front-end
# --------------------------------------------------------------------------
def list_doencas() -> list[dict]:
    rows = _fetch_all(
        lambda: get_client().table(T_ZOONOSES).select("id,name").order("id")
    )
    return sorted(
        ({"id": r["id"], "nome": r["name"]} for r in rows),
        key=lambda r: (r["nome"] or "").lower(),
    )


def list_hospedeiros() -> list[dict]:
    rows = _fetch_all(
        lambda: get_client()
        .table(T_HOSPEDEIROS)
        .select("id,name,scientific_name")
        .order("id")
    )
    return sorted(
        (
            {
                "id": r["id"],
                "nome": r["name"],
                "nome_cientifico": r.get("scientific_name"),
            }
            for r in rows
        ),
        key=lambda r: (r["nome"] or "").lower(),
    )


def list_locais() -> list[dict]:
    rows = _fetch_all(
        lambda: get_client().table(T_LOCAIS).select("id,pais,cidade").order("id")
    )
    return [{"pais": r["pais"], "cidade": r["cidade"]} for r in rows]


# --------------------------------------------------------------------------
# Casos identificados
# --------------------------------------------------------------------------
def _resolve_zoonose_ids(f: CasoFilters) -> list[int] | None:
    """Combina os filtros de doença e de hospedeiro em uma lista de zoonose_id.

    None  -> sem restrição por doença/hospedeiro
    []    -> filtros combinados não casam com nenhuma doença
    """
    ids: set[int] | None = set(f.doencas) if f.doencas else None
    if f.hospedeiros:
        rows = _fetch_all(
            lambda: get_client()
            .table(T_ZOONOSE_HOSPEDEIRO)
            .select("zoonose_id")
            .in_("especie_hospedeiro_id", list(f.hospedeiros))
            .order("id")
        )
        por_hospedeiro = {r["zoonose_id"] for r in rows}
        ids = por_hospedeiro if ids is None else ids & por_hospedeiro
    return None if ids is None else sorted(ids)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value[:10]) if value else None


def _normalize(row: dict) -> dict:
    zoonose = row.get("zoonoses") or {}
    local = row.get("locais") or {}
    fonte = row.get("fontes") or {}
    return {
        "doenca_id": row["zoonose_id"],
        "doenca": zoonose.get("name"),
        "local_id": row["local_id"],
        "pais": local.get("pais"),
        "cidade": local.get("cidade"),
        "data": _parse_date(fonte.get("data_publicacao")),
        "ocorrencias_animal": row.get("quantidade_animal") or 0,
        "ocorrencias_humano": row.get("quantidade_humano") or 0,
        "mortes_animal": row.get("obitos_animal") or 0,
        "mortes_humano": row.get("obitos_humano") or 0,
    }


FONTE_COLUMNS_BASICO = "data_publicacao"
FONTE_COLUMNS_COMPLETO = "id,titulo,url,resumo_llm_pt,resumo_llm_en,resumo_llm_es,idioma_original,data_publicacao"


def _fetch_casos_raw(f: CasoFilters, fonte_columns: str) -> list[dict]:
    """Casos com doença, local e fonte embutidos (um nível de relacionamento)."""
    zoonose_ids = _resolve_zoonose_ids(f)
    if zoonose_ids is not None and not zoonose_ids:
        return []

    # "!inner" faz o filtro na tabela relacionada descartar as linhas de casos.
    local_embed = (
        "locais!inner(id,pais,cidade)"
        if (f.pais or f.cidade)
        else "locais(id,pais,cidade)"
    )
    fonte_join = "fontes!inner" if (f.data_inicio or f.data_fim) else "fontes"
    select = ",".join(
        [
            "id,zoonose_id,local_id,quantidade_animal,quantidade_humano,obitos_animal,obitos_humano",
            "zoonoses(id,name)",
            local_embed,
            f"{fonte_join}({fonte_columns})",
        ]
    )

    def build():
        q = get_client().table(T_CASOS).select(select)
        if zoonose_ids is not None:
            q = q.in_("zoonose_id", zoonose_ids)
        if f.pais:
            q = q.eq("locais.pais", f.pais)
        if f.cidade:
            q = q.eq("locais.cidade", f.cidade)
        if f.data_inicio:
            q = q.gte("fontes.data_publicacao", f.data_inicio.isoformat())
        if f.data_fim:
            q = q.lte("fontes.data_publicacao", f.data_fim.isoformat())
        return q.order("id")

    return _fetch_all(build)


def fetch_casos(f: CasoFilters) -> list[dict]:
    """Casos já "achatados" (doença, local, data de publicação e contagens)."""
    return [_normalize(r) for r in _fetch_casos_raw(f, FONTE_COLUMNS_BASICO)]


def _normalize_fonte(row: dict) -> dict:
    zoonose = row.get("zoonoses") or {}
    local = row.get("locais") or {}
    fonte = row.get("fontes") or {}
    return {
        "fonte_id": fonte.get("id"),
        "titulo": fonte.get("titulo"),
        "url": fonte.get("url"),
        "resumo_pt": fonte.get("resumo_llm_pt"),
        "resumo_en": fonte.get("resumo_llm_en"),
        "resumo_es": fonte.get("resumo_llm_es"),
        "idioma_original": fonte.get("idioma_original"),
        "data": _parse_date(fonte.get("data_publicacao")),
        "doenca_id": row["zoonose_id"],
        "doenca": zoonose.get("name"),
        "pais": local.get("pais"),
        "cidade": local.get("cidade"),
    }


def fetch_fontes(f: CasoFilters) -> list[dict]:
    """Uma linha por (fonte, doença, local) citados em casos; agrupe com services.group_fontes."""
    rows = (_normalize_fonte(r) for r in _fetch_casos_raw(f, FONTE_COLUMNS_COMPLETO))
    return [r for r in rows if r["fonte_id"] is not None]
