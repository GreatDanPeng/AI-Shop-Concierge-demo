"""FastAPI app for the concierge demo. Run: uvicorn app.server:app --reload

Unofficial concept demo with fake data. The "login" is a demo-only cookie set by
/demo/switch-member. The member ALWAYS comes from that cookie on the server: no query
parameter or request body can name a member.

The built web app (web/dist) is served from the same origin at "/", so there is no CORS and the
cookie just works. API routes are registered first, so they win over the static files.
"""
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .assistant import (AssistantUnavailable, ConfigError, UnknownStoreError, build_client,
                        provider_status, run_assistant)
from .catalog import load_stores
from .clock import today
from .engine import load_members
from .env import load_env_file
from .matching import describe_identity, estimate, match_offers
from .tools import MAX_CART_CENTS  # one limit for the web API and for the model's tool

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
MAX_MESSAGE_CHARS = 2000
MEMBER_IDS = {m["id"] for m in load_members()}

api = APIRouter()


class SwitchBody(BaseModel):
    member_id: str


class ChatBody(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a member id (or anything else) in the body is refused

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    store_id: str | None = Field(default=None, max_length=64)  # page context from the browser: untrusted

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


def current_member(member_id: str | None = Cookie(default=None)) -> dict:
    """The signed-in member, from the server-side cookie only."""
    if member_id not in MEMBER_IDS:
        raise HTTPException(status_code=401, detail="not_signed_in")
    member = next((m for m in load_members() if m["id"] == member_id), None)
    if member is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    return member


@lru_cache(maxsize=1)
def _client():
    """One API client for the whole process (built on first use, so a missing key fails per request)."""
    return build_client()


@api.get("/health")
def health():
    """Whether the assistant is configured, and with which model. Never a key."""
    return {"ok": True, "assistant": provider_status()}


@api.get("/demo/members")
def demo_members():
    """The demo profiles for the sign-in picker. Demo only: it goes away with a real login."""
    members = []
    day = today()
    for m in load_members():
        identity = describe_identity(m, day)
        members.append({
            "id": m["id"],
            "display_name": m["display_name"],
            "verifications": [{"group": v["group"], "status": v["status"]}
                              for v in identity["verifications"]],
        })
    return members


@api.post("/demo/switch-member")
def switch_member(body: SwitchBody, response: Response):
    if body.member_id not in MEMBER_IDS:
        raise HTTPException(status_code=404, detail="unknown_member")
    response.set_cookie("member_id", body.member_id, httponly=True, samesite="lax")
    return {"ok": True}


@api.get("/me")
def me(member: dict = Depends(current_member)):
    return describe_identity(member, today())


@api.get("/discounts")
def discounts(member: dict = Depends(current_member)):
    day = today()  # once, so the date and the matching always agree
    return {"as_of": day.isoformat(), "stores": match_offers(member, day)}


@api.get("/estimate")
def estimate_cart(store_id: str = Query(min_length=1, max_length=64),
                  cart_cents: int = Query(gt=0, le=MAX_CART_CENTS),
                  member: dict = Depends(current_member)):
    if store_id not in {s["id"] for s in load_stores()}:
        raise HTTPException(status_code=400, detail="unknown_store")
    return estimate(member, store_id, cart_cents, today())


@api.post("/chat")
def chat(body: ChatBody, member: dict = Depends(current_member)):
    """Ask the concierge. Returns only the reply (never the tool calls)."""
    try:
        result = run_assistant(body.message, member["id"], body.store_id, client=_client())
    except UnknownStoreError:
        raise HTTPException(status_code=400, detail="unknown_store") from None
    except ConfigError:
        raise HTTPException(status_code=503, detail="assistant_not_configured") from None
    except AssistantUnavailable:
        raise HTTPException(status_code=502, detail="assistant_unavailable") from None
    return {"reply": result.reply}


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    load_env_file()  # the real .env, if there is one; its values are never logged
    yield


def mount_web(application: FastAPI, dist: Path = WEB_DIST) -> bool:
    """Serve the built web app at "/" (after the API routes). Returns whether a build was found."""
    if (dist / "index.html").is_file():
        application.mount("/", StaticFiles(directory=dist, html=True), name="web")
        return True

    @application.get("/", include_in_schema=False)
    def not_built():
        return {"service": "Concierge demo (unofficial concept demo, fake data)",
                "hint": "The web app is not built yet. Run `npm install && npm run build` in web/."}

    return False


def create_app(web_dist: Path | None = WEB_DIST) -> FastAPI:
    application = FastAPI(title="Concierge demo (unofficial concept demo, fake data)",
                          lifespan=_lifespan)
    application.include_router(api)
    if web_dist is not None:
        mount_web(application, web_dist)
    return application


app = create_app()
