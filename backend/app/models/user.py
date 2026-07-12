import enum

from sqlalchemy import Boolean, Enum, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="roleenum"),
        nullable=False,
        default=RoleEnum.teacher,
        server_default=text("'teacher'"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )