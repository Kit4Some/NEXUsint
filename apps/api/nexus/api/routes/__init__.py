"""REST API route aggregation."""

from fastapi import APIRouter

from nexus.api.routes.auth import router as auth_router
from nexus.api.routes.entities import router as entities_router
from nexus.api.routes.investigations import router as investigations_router
from nexus.api.routes.map import router as map_router
from nexus.api.routes.collection import router as collection_router
from nexus.api.routes.analytics import router as analytics_router
from nexus.api.routes.sigint import router as sigint_router
from nexus.api.routes.socmint import router as socmint_router
from nexus.api.routes.fusion import router as fusion_router
from nexus.api.routes.geoint import router as geoint_router
from nexus.api.routes.ontology import router as ontology_router
from nexus.api.routes.stix import router as stix_router
from nexus.api.routes.reports import router as reports_router
from nexus.api.routes.search import router as search_router
from nexus.api.routes.dashboard import router as dashboard_router
from nexus.api.routes.seed import router as seed_router
from nexus.api.routes.chat import router as chat_router
from nexus.api.routes.monitoring import router as monitoring_router
from nexus.api.routes.live_feed import router as live_feed_router
from nexus.api.routes.news import router as news_router
from nexus.api.routes.radio import router as radio_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(entities_router, prefix="/entities", tags=["Entities"])
router.include_router(investigations_router, prefix="/investigations", tags=["Investigations"])
router.include_router(map_router, prefix="/map", tags=["Map"])
router.include_router(collection_router, prefix="/collect", tags=["Collection"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
router.include_router(sigint_router, prefix="/sigint", tags=["SIGINT"])
router.include_router(socmint_router, prefix="/socmint", tags=["SOCMINT"])
router.include_router(fusion_router, prefix="/fusion", tags=["Fusion"])
router.include_router(geoint_router, prefix="/geoint", tags=["GEOINT"])
router.include_router(ontology_router, prefix="/ontology", tags=["Ontology"])
router.include_router(stix_router, prefix="/stix", tags=["STIX"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
router.include_router(search_router, prefix="/search", tags=["Search"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(seed_router, prefix="/seed", tags=["Seed"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])
router.include_router(live_feed_router, prefix="/live", tags=["Live Feed"])
router.include_router(news_router, prefix="/news", tags=["News"])
router.include_router(radio_router, prefix="/radio", tags=["Radio"])
