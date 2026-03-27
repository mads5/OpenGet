import stripe
from app.core.config import get_settings

_initialized = False


def ensure_stripe_initialized() -> None:
    global _initialized
    if not _initialized:
        settings = get_settings()
        if settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key
        _initialized = True
