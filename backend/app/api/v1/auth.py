from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user, TokenData
from app.models.models import User, CPSE
from app.schemas.schemas import UserLogin, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    # Local developer fast bypass or DB check
    user = await db.execute(select(User).filter(User.username == credentials.username))
    user_obj = user.scalars().first()
    
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
        
    if not verify_password(credentials.password, user_obj.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
        
    cpse_code = user_obj.cpse.code if user_obj.cpse else None
    token = create_access_token({"sub": user_obj.username, "role": user_obj.role, "cpse_id": user_obj.cpse_id})
    return Token(access_token=token, token_type="bearer", role=user_obj.role, username=user_obj.username, cpse_code=cpse_code)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: TokenData = Depends(get_current_user)):
    return UserResponse(
        id=1,
        username=current_user.username,
        email=f"{current_user.username}@unimm.gov.in",
        role=current_user.role,
        cpse_id=current_user.cpse_id,
        created_at=datetime.utcnow()
    )
