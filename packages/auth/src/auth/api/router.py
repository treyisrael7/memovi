from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from auth.api.dependencies import (
    SESSION_COOKIE_NAME,
    SESSION_TTL,
    get_current_user_query,
    get_login_user,
    get_logout_user,
    get_register_user,
)
from auth.api.schemas import AuthCredentialsRequest, UserResponse
from auth.application.commands import (
    LoginUser,
    LoginUserCommand,
    LogoutUser,
    RegisterUser,
    RegisterUserCommand,
)
from auth.application.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UnauthenticatedError,
)
from auth.application.queries import GetCurrentUser
from auth.domain.exceptions import AuthDomainError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: AuthCredentialsRequest,
    response: Response,
    use_case: Annotated[RegisterUser, Depends(get_register_user)],
) -> UserResponse:
    try:
        result = use_case.execute(
            RegisterUserCommand(email=request.email, password=request.password),
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered.",
        ) from exc
    except AuthDomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    set_session_cookie(response, result.session_token)
    return UserResponse.model_validate(result.user)


@router.post("/login", response_model=UserResponse)
def login(
    request: AuthCredentialsRequest,
    response: Response,
    use_case: Annotated[LoginUser, Depends(get_login_user)],
) -> UserResponse:
    try:
        result = use_case.execute(LoginUserCommand(email=request.email, password=request.password))
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email address or password is incorrect.",
        ) from exc
    except AuthDomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    set_session_cookie(response, result.session_token)
    return UserResponse.model_validate(result.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    use_case: Annotated[LogoutUser, Depends(get_logout_user)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> None:
    use_case.execute(session_token)
    clear_session_cookie(response)


@router.get("/me", response_model=UserResponse)
def me(
    use_case: Annotated[GetCurrentUser, Depends(get_current_user_query)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> UserResponse:
    try:
        user = use_case.execute(session_token)
    except UnauthenticatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        ) from exc

    return UserResponse.model_validate(user)


def set_session_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
    )
