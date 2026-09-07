from src.api.routes.approvals import router as approvals_router
from src.api.routes.clients import clients_router, conv_router, prop_router
from src.api.routes.health import router as health_router
from src.api.routes.leads import router as leads_router
from src.api.routes.lifecycle import router as lifecycle_router
from src.api.routes.outbox import router as outbox_router

__all__ = [
    "health_router",
    "leads_router",
    "clients_router",
    "conv_router",
    "prop_router",
    "lifecycle_router",
    "outbox_router",
    "approvals_router",
]
