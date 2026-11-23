# API de Zoonoses (somente leitura)

API em Django + Django REST Framework que lê o banco **Supabase** (PostgreSQL) e alimenta o site de relatório de zoonoses.

## Ambientes (dev / produção)

O ambiente é escolhido por `APP_ENV` no arquivo `.env`:

| APP_ENV       | Projeto Supabase     | Variáveis usadas                      |
|---------------|----------------------|---------------------------------------|
| `development` | `pampa-zoonoses-dev` | `SUPABASE_URL_DEV`, `SUPABASE_KEY_DEV`|
| `production`  | `pampa-zoonoses`     | `SUPABASE_URL`, `SUPABASE_KEY`        |

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha as variáveis
python manage.py runserver  # http://localhost:8000/api/v1/health/
```

Produção: `APP_ENV=production gunicorn config.wsgi` (exige `DJANGO_SECRET_KEY`; defina também `DJANGO_ALLOWED_HOSTS` e `CORS_ALLOWED_ORIGINS`).

## Endpoints (todos `GET`)

Prefixo: `/api/v1/`. Qualquer outro método retorna `405`.

### Listas para os filtros
| Rota | Retorno |
|---|---|
| `doencas/` | `[{id, nome}]` |
| `hospedeiros/` | `[{id, nome, nome_cientifico}]` |
| `paises/` | `["Brasil", ...]` |
| `cidades/?pais=Brasil` | `["Santiago", ...]` (`pais` opcional) |

### Filtros (comuns a `mapa/`, `estatisticas/doencas/` e `estatisticas/crescimento/`)
| Parâmetro | Exemplo | Observação |
|---|---|---|
| `doenca` | `1,2` | IDs de `zoonoses` |
| `hospedeiro` | `3` | IDs de `especies_hospedeiro`; filtra as doenças associadas ao hospedeiro (`zoonose_hospedeiro`) |
| `pais` | `Brasil` | valor exato, como retornado por `paises/` |
| `cidade` | `Santiago` | valor exato, como retornado por `cidades/` |
| `data_inicio`, `data_fim` | `2026-01-01` | filtram por `fontes.data_publicacao` |

### `GET mapa/` — bolhas do mapa
Uma entrada por local, com totais e detalhamento por doença:
```json
{
  "total": {"ocorrencias": 120, "mortes": 9, "...": 0},
  "locais": [
    {"local_id": 4, "pais": "Brasil", "cidade": "Santiago",
     "ocorrencias": 40, "ocorrencias_animal": 35, "ocorrencias_humano": 5,
     "mortes": 3, "mortes_animal": 3, "mortes_humano": 0,
     "doencas": [{"doenca_id": 1, "doenca": "Raiva", "ocorrencias": 25, "mortes": 3, "...": 0}]}
  ]
}
```

### `GET fontes/` e `GET doencas/<id>/fontes/` — fontes dos casos
Lista as fontes (título, resumo gerado por IA e link original) que embasam os casos. Aceita os mesmos filtros acima; em `doencas/<id>/fontes/` o `id` da rota substitui `?doenca=`.
Parâmetros extras: `idioma=pt|en|es` (idioma do resumo, padrão `pt`), `pagina` (padrão 1) e `limite` (padrão 50, máx. 200).
Ordenadas da publicação mais recente para a mais antiga (sem data por último).
```json
{
  "total": 42, "pagina": 1, "limite": 50,
  "resultados": [
    {"fonte_id": 7, "titulo": "Surto de raiva ...", "url": "https://...",
     "resumo": "Resumo gerado por IA ...", "idioma_resumo": "pt",
     "idioma_original": "Português", "data_publicacao": "2026-03-05",
     "doencas": [{"doenca_id": 1, "doenca": "Raiva"}],
     "locais": [{"pais": "Brasil", "cidade": "Santiago"}]}
  ]
}
```
`resumo` é `null` quando a fonte não tem resumo no idioma pedido. Com filtro de local, `doencas` e `locais` trazem só o que casa com o filtro.

### `GET estatisticas/doencas/` — totais por doença
`{"total": {...}, "doencas": [{"doenca_id", "doenca", "ocorrencias", "mortes", ...}]}`

### `GET estatisticas/crescimento/` — crescimento no período
Compara `[data_inicio, data_fim]` com o período **imediatamente anterior de mesma duração**.
Padrão: últimos 30 dias. `granularidade=dia|semana|mes` (padrão `mes`) controla a série temporal.
```json
{
  "periodo": {"inicio": "2026-03-01", "fim": "2026-03-31", "dias": 31},
  "periodo_anterior": {"inicio": "2026-01-29", "fim": "2026-02-28"},
  "total": {"ocorrencias": {"atual": 19, "anterior": 16, "variacao_absoluta": 3, "variacao_percentual": 18.75},
            "mortes": {"...": 0}},
  "doencas": [{"doenca_id": 1, "doenca": "Raiva", "ocorrencias": {"...": 0}, "mortes": {"...": 0}}],
  "serie_temporal": [{"inicio": "2026-03-01", "ocorrencias": 12, "mortes": 1}]
}
```
`variacao_percentual` é `null` quando não havia casos no período anterior (não existe base de comparação).


## Testes
```bash
python -m unittest tests.test_services                      # lógica de cálculo (sem dependências)
APP_ENV=development SUPABASE_URL_DEV=http://x SUPABASE_KEY_DEV=x python manage.py test   # views
```
