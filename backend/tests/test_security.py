from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import RoleEnum


def test_password_hash_and_verify() -> None:
    password = "StrongPassword123!"

    hashed_password = get_password_hash(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False


def test_jwt_contains_user_id_and_role() -> None:
    token = create_access_token(
        user_id=123,
        role=RoleEnum.admin,
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert payload["role"] == "admin"
    assert "exp" in payload
