"""Cálculos sobre os casos (funções puras, sem Django nem rede)."""

from __future__ import annotations

from datetime import date, timedelta

METRICS = ("ocorrencias_animal", "ocorrencias_humano", "mortes_animal", "mortes_humano")
GRANULARIDADES = ("dia", "semana", "mes")


def _zero() -> dict:
    return dict.fromkeys(METRICS, 0)


def _add(acc: dict, row: dict) -> None:
    for m in METRICS:
        acc[m] += row[m]


def _with_totals(acc: dict) -> dict:
    return {
        "ocorrencias": acc["ocorrencias_animal"] + acc["ocorrencias_humano"],
        "ocorrencias_animal": acc["ocorrencias_animal"],
        "ocorrencias_humano": acc["ocorrencias_humano"],
        "mortes": acc["mortes_animal"] + acc["mortes_humano"],
        "mortes_animal": acc["mortes_animal"],
        "mortes_humano": acc["mortes_humano"],
    }


def summarize(rows: list[dict]) -> dict:
    acc = _zero()
    for r in rows:
        _add(acc, r)
    return _with_totals(acc)


# --------------------------------------------------------------------------
# Contagem por doença
# --------------------------------------------------------------------------
def by_disease(rows: list[dict]) -> list[dict]:
    groups: dict[int, dict] = {}
    for r in rows:
        g = groups.setdefault(r["doenca_id"], {"nome": r["doenca"], "acc": _zero()})
        _add(g["acc"], r)
    result = [
        {"doenca_id": did, "doenca": g["nome"], **_with_totals(g["acc"])}
        for did, g in groups.items()
    ]
    return sorted(result, key=lambda x: (-x["ocorrencias"], x["doenca"] or ""))


# --------------------------------------------------------------------------
# Bolhas do mapa: uma por local, com o detalhamento por doença
# --------------------------------------------------------------------------
def map_bubbles(rows: list[dict]) -> list[dict]:
    locais: dict[int, dict] = {}
    for r in rows:
        loc = locais.setdefault(
            r["local_id"],
            {"pais": r["pais"], "cidade": r["cidade"], "acc": _zero(), "doencas": {}},
        )
        _add(loc["acc"], r)
        d = loc["doencas"].setdefault(
            r["doenca_id"], {"nome": r["doenca"], "acc": _zero()}
        )
        _add(d["acc"], r)

    result = []
    for local_id, loc in locais.items():
        doencas = sorted(
            (
                {"doenca_id": did, "doenca": d["nome"], **_with_totals(d["acc"])}
                for did, d in loc["doencas"].items()
            ),
            key=lambda x: (-x["ocorrencias"], x["doenca"] or ""),
        )
        result.append(
            {
                "local_id": local_id,
                "pais": loc["pais"],
                "cidade": loc["cidade"],
                **_with_totals(loc["acc"]),
                "doencas": doencas,
            }
        )
    return sorted(
        result, key=lambda x: (-x["ocorrencias"], x["pais"] or "", x["cidade"] or "")
    )


# --------------------------------------------------------------------------
# Crescimento em um período
# --------------------------------------------------------------------------
def resolve_period(
    inicio: date | None,
    fim: date | None,
    hoje: date | None = None,
    default_days: int = 30,
) -> tuple[date, date]:
    """Preenche o que faltar: fim = hoje; início = fim - (default_days - 1)."""
    fim = fim or hoje or date.today()
    inicio = inicio or fim - timedelta(days=default_days - 1)
    return inicio, fim


def previous_period(inicio: date, fim: date) -> tuple[date, date]:
    """Período imediatamente anterior, com a mesma duração."""
    dias = (fim - inicio).days + 1
    return inicio - timedelta(days=dias), inicio - timedelta(days=1)


def variation(atual: int, anterior: int) -> dict:
    """Variação absoluta e percentual. Percentual é None se não havia base (anterior=0, atual>0)."""
    delta = atual - anterior
    if anterior == 0:
        pct = 0.0 if atual == 0 else None
    else:
        pct = round(delta / anterior * 100, 2)
    return {
        "atual": atual,
        "anterior": anterior,
        "variacao_absoluta": delta,
        "variacao_percentual": pct,
    }


def _bucket_start(d: date, granularidade: str) -> date:
    if granularidade == "dia":
        return d
    if granularidade == "semana":
        return d - timedelta(days=d.weekday())  # segunda-feira
    return d.replace(day=1)


def _next_bucket(d: date, granularidade: str) -> date:
    if granularidade == "dia":
        return d + timedelta(days=1)
    if granularidade == "semana":
        return d + timedelta(days=7)
    return (d.replace(day=1) + timedelta(days=32)).replace(day=1)


def time_series(
    rows: list[dict], inicio: date, fim: date, granularidade: str
) -> list[dict]:
    """Série temporal do período, com os intervalos sem casos preenchidos com zero."""
    buckets: dict[date, dict] = {}
    cursor = _bucket_start(inicio, granularidade)
    while cursor <= fim:
        buckets[cursor] = _zero()
        cursor = _next_bucket(cursor, granularidade)
    for r in rows:
        if r["data"] and inicio <= r["data"] <= fim:
            _add(buckets[_bucket_start(r["data"], granularidade)], r)
    return [
        {
            "inicio": b.isoformat(),
            "ocorrencias": acc["ocorrencias_animal"] + acc["ocorrencias_humano"],
            "mortes": acc["mortes_animal"] + acc["mortes_humano"],
        }
        for b, acc in buckets.items()
    ]


def growth_report(
    rows: list[dict], inicio: date, fim: date, granularidade: str = "mes"
) -> dict:
    """Compara o período [inicio, fim] com o período anterior de mesma duração.

    `rows` deve conter os casos de ambos os períodos; casos sem data são ignorados.
    """
    ant_inicio, ant_fim = previous_period(inicio, fim)
    atual = [r for r in rows if r["data"] and inicio <= r["data"] <= fim]
    anterior = [r for r in rows if r["data"] and ant_inicio <= r["data"] <= ant_fim]

    cur_by = {d["doenca_id"]: d for d in by_disease(atual)}
    prev_by = {d["doenca_id"]: d for d in by_disease(anterior)}
    nomes = {r["doenca_id"]: r["doenca"] for r in rows}

    doencas = []
    for did in sorted(set(cur_by) | set(prev_by)):
        c, p = cur_by.get(did, {}), prev_by.get(did, {})
        doencas.append(
            {
                "doenca_id": did,
                "doenca": nomes.get(did),
                "ocorrencias": variation(
                    c.get("ocorrencias", 0), p.get("ocorrencias", 0)
                ),
                "mortes": variation(c.get("mortes", 0), p.get("mortes", 0)),
            }
        )
    doencas.sort(key=lambda d: (-d["ocorrencias"]["atual"], d["doenca"] or ""))

    tot_c, tot_p = summarize(atual), summarize(anterior)
    return {
        "periodo": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "dias": (fim - inicio).days + 1,
        },
        "periodo_anterior": {
            "inicio": ant_inicio.isoformat(),
            "fim": ant_fim.isoformat(),
        },
        "total": {
            "ocorrencias": variation(tot_c["ocorrencias"], tot_p["ocorrencias"]),
            "mortes": variation(tot_c["mortes"], tot_p["mortes"]),
        },
        "doencas": doencas,
        "granularidade": granularidade,
        "serie_temporal": time_series(atual, inicio, fim, granularidade),
    }


# --------------------------------------------------------------------------
# Fontes (artigos/notícias) que embasam os casos
# --------------------------------------------------------------------------
IDIOMAS_RESUMO = ("pt", "en", "es")


def group_fontes(rows: list[dict], idioma: str = "pt") -> list[dict]:
    """Agrupa as linhas por fonte, reunindo as doenças e os locais citados em cada uma.

    Ordem: publicação mais recente primeiro (sem data por último).
    """
    fontes: dict[int, dict] = {}
    for r in rows:
        f = fontes.setdefault(
            r["fonte_id"],
            {
                "fonte_id": r["fonte_id"],
                "titulo": r["titulo"],
                "url": r["url"],
                "resumo": r.get(f"resumo_{idioma}"),
                "idioma_resumo": idioma,
                "idioma_original": r["idioma_original"],
                "data_publicacao": r["data"].isoformat() if r["data"] else None,
                "doencas": {},
                "locais": {},
            },
        )
        f["doencas"][r["doenca_id"]] = r["doenca"]
        f["locais"][(r["pais"], r["cidade"])] = None

    result = [
        {
            **{k: v for k, v in f.items() if k not in ("doencas", "locais")},
            "doencas": [
                {"doenca_id": i, "doenca": n}
                for i, n in sorted(f["doencas"].items(), key=lambda x: x[1] or "")
            ],
            "locais": [
                {"pais": p, "cidade": c}
                for p, c in sorted(f["locais"], key=lambda x: (x[0] or "", x[1] or ""))
            ],
        }
        for f in fontes.values()
    ]
    # data desc (None por último), depois id desc
    result.sort(key=lambda f: f["fonte_id"], reverse=True)
    result.sort(key=lambda f: f["data_publicacao"] or "", reverse=True)
    com_data = [f for f in result if f["data_publicacao"]]
    sem_data = [f for f in result if not f["data_publicacao"]]
    return com_data + sem_data


def paginate(items: list, pagina: int, limite: int) -> dict:
    inicio = (pagina - 1) * limite
    return {
        "total": len(items),
        "pagina": pagina,
        "limite": limite,
        "resultados": items[inicio : inicio + limite],
    }
