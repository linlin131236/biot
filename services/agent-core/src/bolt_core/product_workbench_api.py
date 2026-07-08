from fastapi import APIRouter

from bolt_core.product_workbench import ProductWorkbenchService


def create_product_workbench_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["product-workbench"])
    service = ProductWorkbenchService(project_dir)

    @router.get("/product-workbench")
    def product_workbench() -> dict:
        return service.snapshot().to_dict()

    return router
