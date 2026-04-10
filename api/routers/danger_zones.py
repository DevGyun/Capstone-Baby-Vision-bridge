from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.base import AsyncSessionLocal
from db.models import DangerZone, Camera
from pydantic import BaseModel
from core.security import decode_access_token

router = APIRouter(prefix="/danger-zones", tags=["danger_zones"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_current_user_id(authorization: str = Header(...)) -> int:
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    return int(payload.get("sub"))

class DangerZoneCreate(BaseModel):
    camera_id: int
    label: str | None = None
    zone_points: list

@router.post("")
async def create_danger_zone(
    body: DangerZoneCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 내 카메라인지 확인
    result = await db.execute(select(Camera).where(Camera.id == body.camera_id, Camera.user_id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="카메라를 찾을 수 없어요")

    zone = DangerZone(
        camera_id=body.camera_id,
        label=body.label,
        zone_points=body.zone_points
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone

@router.get("/{camera_id}")
async def get_danger_zones(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # 내 카메라인지 확인
    result = await db.execute(select(Camera).where(Camera.id == camera_id, Camera.user_id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="카메라를 찾을 수 없어요")

    result = await db.execute(select(DangerZone).where(DangerZone.camera_id == camera_id))
    zones = result.scalars().all()
    return zones

@router.delete("/{zone_id}")
async def delete_danger_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(select(DangerZone).where(DangerZone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(status_code=404, detail="위험구역을 찾을 수 없어요")

    await db.delete(zone)
    await db.commit()
    return {"detail": "삭제됐어요"}
