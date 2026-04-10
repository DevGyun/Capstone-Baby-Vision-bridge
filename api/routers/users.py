from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.base import AsyncSessionLocal
from db.models import User
from schemas.users import UserCreate, UserLogin, TokenResponse
from core.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/users", tags=["users"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/register")
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    # 이메일 중복 확인
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일이에요")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email}

@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸어요")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token}

@router.get("/me")
async def get_me(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    user_id = int(payload.get("sub"))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없어요")

    return {"id": user.id, "email": user.email, "name": user.name}
