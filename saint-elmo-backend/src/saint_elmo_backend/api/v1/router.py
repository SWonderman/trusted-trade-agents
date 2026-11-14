from fastapi import APIRouter

from saint_elmo_backend.api.v1.routes.agents import router as agents_router
from saint_elmo_backend.api.v1.routes.auth import router as auth_router
from saint_elmo_backend.api.v1.routes.catalog import router as catalog_router
from saint_elmo_backend.api.v1.routes.offers import router as offers_router
from saint_elmo_backend.api.v1.routes.orders import router as orders_router
from saint_elmo_backend.api.v1.routes.products import router as products_router
from saint_elmo_backend.api.v1.routes.quotes import router as quotes_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(products_router, prefix="/products", tags=["Products"])
router.include_router(catalog_router, prefix="/catalog", tags=["Catalog"])
router.include_router(offers_router, prefix="/offers", tags=["Offers"])
router.include_router(quotes_router, prefix="/quotes", tags=["Quotes"])
router.include_router(orders_router, prefix="/orders", tags=["Orders"])
router.include_router(agents_router, prefix="/agents", tags=["Agents"])
