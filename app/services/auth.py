from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.user import UserCreate
from app.services import audit


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.db = db

    def register(self, payload: UserCreate, actor_ip: str = "") -> User:
        if self.repo.get_by_email(payload.email):
            raise ConflictError("Email already registered")
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role="developer",
        )
        user = self.repo.add(user)
        audit.record(
            self.db,
            actor=user.email,
            action="register",
            resource_type="user",
            resource_id=user.id,
            ip_address=actor_ip,
        )
        return user

    def authenticate(self, email: str, password: str) -> tuple[User, str]:
        user = self.repo.get_by_email(email.strip().lower())
        if (
            not user
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        ):
            raise UnauthorizedError("Incorrect email or password")
        token = create_access_token(user.email, extra={"role": user.role})
        return user, token
