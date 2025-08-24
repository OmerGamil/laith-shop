# shop/cart.py
from decimal import Decimal
from django.utils.translation import gettext as _
from django.db.models import Prefetch

CART_KEY = "cart"


def _ensure(session):
    if CART_KEY not in session:
        session[CART_KEY] = {}
    return session[CART_KEY]


def add(session, product_id: int, qty: int = 1, price: Decimal | float | str | None = None):
    cart = _ensure(session)
    pid = str(product_id)
    item = cart.get(pid, {"qty": 0})
    item["qty"] = max(1, int(item["qty"]) + int(qty))
    if price is not None:
        item["price"] = str(price)
    cart[pid] = item
    session.modified = True
    return cart


def set_qty(session, product_id: int, qty: int):
    cart = _ensure(session)
    pid = str(product_id)
    if qty <= 0:
        cart.pop(pid, None)
    else:
        item = cart.get(pid, {})
        item["qty"] = int(qty)
        cart[pid] = item
    session.modified = True


def remove(session, product_id: int):
    cart = _ensure(session)
    cart.pop(str(product_id), None)
    session.modified = True


def clear(session):
    session[CART_KEY] = {}
    session.modified = True


def items_with_products(session, ProductModel):
    """
    Returns list of dicts: {product, qty, unit_price, line_total}

    Now fetches products with category + translations prefetched so
    the view can show localized titles without extra queries.
    """
    cart = _ensure(session)
    if not cart:
        return []
    ids = [int(pid) for pid in cart.keys()]

    products_qs = (
        ProductModel.objects
        .filter(id__in=ids)
        .select_related("category")
        .prefetch_related("translations")  # p.translations usable; views fallback if no tr_list attr
    )

    products = {p.id: p for p in products_qs}
    out = []
    for pid, meta in cart.items():
        p = products.get(int(pid))
        if not p:
            continue
        unit = getattr(p, "sale_price", None) or getattr(p, "price", None)
        try:
            unit = Decimal(str(unit))
        except Exception:
            unit = Decimal("0")
        qty = int(meta.get("qty", 1))
        out.append({
            "product": p,
            "qty": qty,
            "unit_price": unit,
            "line_total": unit * qty,
        })
    return out


def totals(session, ProductModel):
    lines = items_with_products(session, ProductModel)
    subtotal = sum((li["line_total"] for li in lines), start=Decimal("0"))
    return {"subtotal": subtotal, "lines": lines}
