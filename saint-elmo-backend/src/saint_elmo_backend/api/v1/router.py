from fastapi import APIRouter

from saint_elmo_backend.api.v1.routes.agents import router as agents_router
from saint_elmo_backend.api.v1.routes.auth import router as auth_router
from saint_elmo_backend.api.v1.routes.catalog import router as catalog_router
from saint_elmo_backend.api.v1.routes.products import router as products_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(products_router, prefix="/products", tags=["Products"])
router.include_router(catalog_router, prefix="/catalog", tags=["Catalog"])
router.include_router(agents_router, prefix="/agents", tags=["Agents"])
