"""
Prometheus Observability & Metrics Module for Sudoku Arena
Fournit l'instrumentation automatique HTTP/WS et les métriques métier
(salles actives, coups joués, victoires joueur vs bot) pour scraping par Prometheus.
"""

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

# --- Métriques Métier Sudoku Arena ---

ACTIVE_ROOMS = Gauge(
    "sudoku_active_rooms",
    "Nombre de salons de Sudoku actuellement actifs en mémoire"
)

GAMES_STARTED_TOTAL = Counter(
    "sudoku_games_started_total",
    "Nombre total de parties de Sudoku lancées",
    ["mode", "difficulty"]
)

MOVES_TOTAL = Counter(
    "sudoku_moves_total",
    "Nombre total de coups soumis par les joueurs",
    ["result", "mode"]
)

WINS_TOTAL = Counter(
    "sudoku_wins_total",
    "Nombre total de victoires enregistrées",
    ["winner_type", "mode"]
)


def setup_metrics(app):
    """
    Initialise l'instrumentation automatique de l'API FastAPI et expose l'endpoint /metrics.
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"]
    )
    instrumentator.instrument(app)

    @app.get("/metrics", tags=["Observability"])
    def metrics_endpoint():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return instrumentator
