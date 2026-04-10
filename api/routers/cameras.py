from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.base import AsyncSessionLocal
from db.models import Camera
from pydantic import BaseModel
from core.security import decode_access_token
import uuid
import os

router = APIRouter(prefix="/cameras", tags=["cameras"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_current_user_id(authorization: str = Header(...)) -> int:
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    return int(payload.get("sub"))

class CameraCreate(BaseModel):
    name: str  # stream_url 제거

@router.post("")
async def create_camera(
    body: CameraCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    server_host = os.getenv("SERVER_HOST", "localhost")
    stream_url = f"rtsp://{server_host}:8554/{uuid.uuid4()}"  # 자동 생성

    camera = Camera(
        user_id=user_id,
        name=body.name,
        stream_url=stream_url
    )
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    return {"id": camera.id, "name": camera.name, "stream_url": camera.stream_url}

@router.get("")
async def get_cameras(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(select(Camera).where(Camera.user_id == user_id))
    cameras = result.scalars().all()
    return cameras

@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id, Camera.user_id == user_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(status_code=404, detail="카메라를 찾을 수 없어요")

    await db.delete(camera)
    await db.commit()
    return {"detail": "삭제됐어요"}
