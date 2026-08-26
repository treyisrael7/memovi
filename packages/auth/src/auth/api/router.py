from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from auth.api.dependencies import (
    SESSION_COOKIE_NAME,
    SESSION_TTL,
    get_current_user_query,
    get_login_user,
    get_logout_user,
    get_register_user,
)
from auth.api.schemas import AuthCredentialsRequest, UserResponse
from auth.api.session_cookies import (
    COOKIE_DELETION_EXPIRES,
    NATIVE_SMOKE_REQUEST_HEADER,
    SESSION_COOKIE_CONTRACT_HEADER,
    SESSION_COOKIE_PATH,
    SESSION_RECEIVED_HEADER,
    SessionCookieFlags,
    cookie_header_value,
    cookie_header_values,
    describe_received_session_cookies,
    describe_session_cookie_contract,
    session_cookie_flags,
)
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

_AUTH_NO_STORE = "no-store"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: AuthCredentialsRequest,
    http_request: Request,
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

    set_session_cookie(response, result.session_token, request=http_request)
    return UserResponse.model_validate(result.user)


@router.post("/login", response_model=UserResponse)
def login(
    request: AuthCredentialsRequest,
    http_request: Request,
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

    set_session_cookie(response, result.session_token, request=http_request)
    return UserResponse.model_validate(result.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    http_request: Request,
    response: Response,
    use_case: Annotated[LogoutUser, Depends(get_logout_user)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> None:
    tokens = cookie_header_values(http_request.headers.get("cookie"), SESSION_COOKIE_NAME)
    if session_token and session_token not in tokens:
        tokens = (session_token, *tokens)
    use_case.execute_many(tokens)
    clear_session_cookie(response, request=http_request)


@router.get("/me", response_model=UserResponse)
def me(
    http_request: Request,
    response: Response,
    use_case: Annotated[GetCurrentUser, Depends(get_current_user_query)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> UserResponse:
    token = session_token or cookie_header_value(
        http_request.headers.get("cookie"),
        SESSION_COOKIE_NAME,
    )
    apply_auth_transport_headers(response, request=http_request)
    try:
        user = use_case.execute(token)
    except UnauthenticatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers=auth_transport_header_map(http_request),
        ) from exc

    return UserResponse.model_validate(user)


def _cookie_flags(request: Request) -> SessionCookieFlags:
    return session_cookie_flags(
        origin=request.headers.get("origin"),
        request_is_https=request.url.scheme == "https",
    )


def auth_transport_header_map(
    request: Request,
    *,
    flags: SessionCookieFlags | None = None,
    deleting: bool = False,
) -> dict[str, str]:
    headers = {"Cache-Control": _AUTH_NO_STORE}
    if request.headers.get(NATIVE_SMOKE_REQUEST_HEADER) != "1":
        return headers
    headers[SESSION_RECEIVED_HEADER] = describe_received_session_cookies(
        request.headers.get("cookie"),
        SESSION_COOKIE_NAME,
    )
    if flags is not None:
        headers[SESSION_COOKIE_CONTRACT_HEADER] = describe_session_cookie_contract(
            name=SESSION_COOKIE_NAME,
            flags=flags,
            deleting=deleting,
        )
    return headers


def apply_auth_transport_headers(
    response: Response,
    *,
    request: Request,
    flags: SessionCookieFlags | None = None,
    deleting: bool = False,
) -> None:
    for key, value in auth_transport_header_map(
        request,
        flags=flags,
        deleting=deleting,
    ).items():
        response.headers[key] = value


def set_session_cookie(response: Response, session_token: str, *, request: Request) -> None:
    flags = _cookie_flags(request)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=flags.secure,
        samesite=flags.samesite,
        partitioned=flags.partitioned,
    )
    apply_auth_transport_headers(response, request=request, flags=flags, deleting=False)


def clear_session_cookie(response: Response, *, request: Request) -> None:
    flags = _cookie_flags(request)
    # Starlette delete_cookie does not accept partitioned; expire with the same
    # flags. Do not pass expires=0 — Python 3.14 serializes that as "now".
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value="",
        max_age=0,
        expires=COOKIE_DELETION_EXPIRES,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=flags.secure,
        samesite=flags.samesite,
        partitioned=flags.partitioned,
    )
    apply_auth_transport_headers(response, request=request, flags=flags, deleting=True)
