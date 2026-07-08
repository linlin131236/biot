from fastapi import APIRouter

from bolt_core.product_workbench_dogfood import ProductWorkbenchDogfoodService


def create_product_workbench_dogfood_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["product-workbench-dogfood"])
    service = ProductWorkbenchDogfoodService(project_dir)

    @router.get("/product-workbench-dogfood")
    def product_workbench_dogfood() -> dict:
        return service.run().to_dict()

    return router
