from fastapi import APIRouter

from saint_elmo_backend.api.v1.routes.catalog import router as catalog_router
from saint_elmo_backend.api.v1.routes.products import router as products_router

router = APIRouter(prefix="/api/v1")

router.include_router(products_router, prefix="/products", tags=["Products"])
router.include_router(catalog_router, prefix="/catalog", tags=["Catalog"])
