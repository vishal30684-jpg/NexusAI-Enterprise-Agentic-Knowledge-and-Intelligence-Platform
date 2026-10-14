from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.security import decode_access_token

from backend.database import get_db
from backend.models import User
from backend.schemas import UserCreate, UserResponse, UserLogin, TokenResponse
from backend.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)



router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Hash the password before storing it
    hashed_password = hash_password(user_data.password)

    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    # Find user by email
    user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    # User does not exist
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(
        user_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    # Create JWT
    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
    
    
    
    
def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    try:
        token = credentials.credentials

        payload = decode_access_token(token)

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        return int(user_id)

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )  
        
        
def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    return user        

def require_role(*allowed_roles: str):
    def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        return current_user

    return role_checker
        
@router.get("/me")
def get_my_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active
    }        
    
    
@router.get("/admin-test")
def admin_test(
    current_user: User = Depends(require_role("ADMIN"))
):
    return {
        "message": "Welcome Admin!",
        "user": current_user.email,
        "role": current_user.role
    }
    
    

@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    users = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .order_by(User.id.asc())
        .all()
    )

    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
        for user in users
    ]
    