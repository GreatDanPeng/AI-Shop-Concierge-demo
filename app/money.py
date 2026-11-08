"""Money and percent formatting from integers (integer math only, so no float can creep in)."""


def format_cents(cents: int) -> str:
    """130000 -> '$1,300.00'. Negative amounts keep the sign in front: -250 -> '-$2.50'."""
    if type(cents) is not int:
        raise TypeError("cents must be an int")
    sign = "-" if cents < 0 else ""
    dollars, remainder = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{remainder:02d}"


def headline_label(bps: int) -> str:
    """Basis points as a percentage label using integer math only: 3000 -> '30%', 350 -> '3.5%'."""
    whole, fraction = divmod(bps, 100)
    if fraction == 0:
        return f"{whole}%"
    return f"{whole}.{fraction:02d}".rstrip("0") + "%"


def with_dollars(result: dict) -> dict:
    """The engine's best-combination result plus ready-made dollar strings, as a copy.

    Nobody downstream (the model, the web page) should convert cents itself: a live run turned
    130000 cents into "$130.00". The engine's result is not changed; this adds one key.
    """
    discount = result["group_discount"]["cents"] if result["group_discount"] else 0
    return {**result, "dollars": {
        "cart": format_cents(result["cart_cents"]),
        "group_discount": format_cents(discount),
        "you_pay": format_cents(result["you_pay_cents"]),
        "cash_back": format_cents(result["cash_back_cents"]),
        "total_savings": format_cents(result["total_savings_cents"]),
    }}
