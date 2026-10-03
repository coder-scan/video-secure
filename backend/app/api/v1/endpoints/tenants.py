from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.tenant import TenantResponse

router = APIRouter()


@router.get("/my-organization", response_model=TenantResponse)
async def get_my_organization(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
):
    return current_tenant
