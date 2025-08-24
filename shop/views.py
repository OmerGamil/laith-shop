# shop/views.py
from __future__ import annotations

import re
from decimal import Decimal

from django.db.models import Q, Prefetch
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.utils.translation import get_language, gettext as _

from .models import Product, ProductTranslation
from .cart import (
    add as cart_add,
    set_qty as cart_set_qty,
    remove as cart_remove,
    clear as cart_clear,
    totals as cart_totals,
)

# ---------------------------------------------------------
# Language helpers & display-field decoration
# ---------------------------------------------------------

def _short_lang(default: str = "de") -> str:
    """Return 'de' / 'ar' etc., short code without region."""
    return (get_language() or default).lower().split("-")[0]


def _prefetch(qs):
    """Prefetch category and all translations into p.tr_list."""
    return qs.select_related("category").prefetch_related(
        Prefetch(
            "translations",
            queryset=ProductTranslation.objects.all(),
            to_attr="tr_list",
        )
    )


def _cat_display_title(cat, ui_short: str) -> str:
    """Pick category label in the UI language."""
    if not cat:
        return _("Sonstiges")
    name_de = getattr(cat, "name_de", None)
    name_ar = getattr(cat, "name_ar", None)
    generic = getattr(cat, "name", None) or getattr(cat, "title", None) or str(cat)
    # Arabic UI prefers AR, fallback DE; German UI prefers DE, fallback generic/AR
    return (name_ar or name_de or generic) if ui_short == "ar" else (name_de or generic or name_ar)


def _pick_translation(tr_list, ui_short: str, default_short: str = "de"):
    """Choose the best translation object from a list."""
    if not tr_list:
        return None
    preferred = ["ar", default_short] if ui_short == "ar" else [ui_short, default_short]

    def code_of(t):
        code = (getattr(t, "language_code", None) or getattr(t, "language", "")).lower()
        return code.split("-")[0]

    for want in preferred:
        for t in tr_list:
            if code_of(t) == want:
                return t
    return tr_list[0]


def _decorate_product(p: Product, ui_short: str, default_lang: str = "de") -> Product:
    """
    Attach display fields to a Product instance:

      - p.display_title
      - p.display_description
      - p.category_display_title

    This is resilient even if no prefetch was used (it will fall back to
    querying p.translations for cart-sized lists).
    """
    # Prefer prefetched list; otherwise fall back to an on-demand fetch (cart is small)
    tr_list = getattr(p, "tr_list", None)
    if tr_list is None:
        try:
            tr_list = list(p.translations.all())
        except Exception:
            tr_list = []

    tr = _pick_translation(tr_list, ui_short, default_lang)
    raw_title = getattr(p, "slug", None) or str(p)  # a safe fallback
    raw_desc = ""

    p.display_title = (getattr(tr, "title", None) or raw_title) if tr else raw_title
    p.display_description = (getattr(tr, "description", None) or raw_desc) if tr else raw_desc
    p.category_display_title = _cat_display_title(getattr(p, "category", None), ui_short)
    return p


# ---------------------------------------------------------
# Product fetching / search / grouping
# ---------------------------------------------------------

def _language_agnostic_filter(qs, q: str):
    """
    Filter by words across:
      - translations.title / translations.description
      - product.slug
      - product.sku
    """
    q = (q or "").strip()
    if not q:
        return qs

    terms = [t for t in re.split(r"\s+", q) if t]
    if not terms:
        return qs

    SEARCH_FIELDS = (
        "translations__title__icontains",
        "translations__description__icontains",
        "slug__icontains",
        "sku__icontains",
    )

    for term in terms:
        term_q = Q()
        for f in SEARCH_FIELDS:
            term_q |= Q(**{f: term})
        qs = qs.filter(term_q)

    return qs.distinct()


def _build_anchor(cat) -> str:
    """Stable anchors so AR/DE labels don’t change the hash targets."""
    return f"cat-{cat.pk}" if cat else "cat-misc"


def _build_sections(request, q: str = ""):
    """
    Single source of truth:
      - fetch products
      - apply language-agnostic search
      - prefetch translations
      - decorate display fields for the current UI lang
      - group by category with stable anchors
    """
    ui_short = _short_lang()
    qs = Product.objects.all().order_by("-id")
    qs = _language_agnostic_filter(qs, q)
    qs = _prefetch(qs)

    grouped = {}
    for p in qs:
        _decorate_product(p, ui_short)
        cat = getattr(p, "category", None)
        anchor = _build_anchor(cat)
        label = p.category_display_title
        bucket = grouped.setdefault(anchor, {"anchor": anchor, "label": label, "products": []})
        bucket["products"].append(p)

    sections = sorted(grouped.values(), key=lambda s: s["label"].lower())
    return sections


# ---------------------------------------------------------
# Small formatting helpers for JSON responses
# ---------------------------------------------------------

def _fmt2(val: Decimal | float | int) -> str:
    try:
        return f"{Decimal(str(val)):.2f}"
    except Exception:
        return "0.00"


def _fmt_display(val: Decimal | float | int) -> str:
    return f"{_fmt2(val)} €"


def _find_line(lines, product_id: int):
    for li in lines:
        if getattr(li.get("product"), "id", None) == product_id:
            return li
    return None


# =========================================================
# CART
# =========================================================

def cart_detail(request):
    ui_short = _short_lang()
    data = cart_totals(request.session, Product)
    # Ensure product.display_title exists for templates (works with/without prefetch)
    for li in data["lines"]:
        prod = li.get("product")
        if prod:
            _decorate_product(prod, ui_short)
    return render(
        request,
        "shop/cart.html",
        {"lines": data["lines"], "subtotal": data["subtotal"]},
    )


@require_POST
def cart_add_view(request):
    pid = request.POST.get("product_id")
    qty = request.POST.get("qty") or "1"
    try:
        product = Product.objects.get(pk=int(pid))
        qty_int = max(1, int(qty))
    except Exception:
        return HttpResponseBadRequest(_("Ungültige Produkt-/Mengenangabe."))

    price = product.sale_price or product.price
    cart_add(request.session, product.id, qty_int, price)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = cart_totals(request.session, Product)
        count = sum(li["qty"] for li in data["lines"])
        return JsonResponse(
            {
                "ok": True,
                "count": count,
                "subtotal": _fmt2(data["subtotal"]),
                "subtotal_display": _fmt_display(data["subtotal"]),
                "cart_url": reverse("shop:cart"),
                "msg": _("Zum Warenkorb hinzugefügt."),
            }
        )
    return redirect("shop:cart")


@require_POST
def cart_update_qty_view(request):
    pid = request.POST.get("product_id")
    qty = request.POST.get("qty")
    try:
        pid_i = int(pid)
        qty_i = int(qty)
        cart_set_qty(request.session, pid_i, qty_i)
    except Exception:
        return HttpResponseBadRequest(_("Ungültige Aktualisierung."))

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = cart_totals(request.session, Product)
        line = _find_line(data["lines"], pid_i) or {}
        unit = line.get("unit_price", Decimal("0"))
        line_total = line.get("line_total", Decimal("0"))
        count = sum(li["qty"] for li in data["lines"])

        return JsonResponse(
            {
                "ok": True,
                "count": count,
                "unit_price": _fmt2(unit),
                "unit_price_display": _fmt_display(unit),
                "line_total": _fmt2(line_total),
                "line_total_display": _fmt_display(line_total),
                "subtotal": _fmt2(data["subtotal"]),
                "subtotal_display": _fmt_display(data["subtotal"]),
            }
        )

    return redirect("shop:cart")


@require_POST
def cart_remove_view(request):
    pid = request.POST.get("product_id")
    try:
        cart_remove(request.session, int(pid))
    except Exception:
        pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = cart_totals(request.session, Product)
        return JsonResponse(
            {
                "ok": True,
                "count": sum(li["qty"] for li in data["lines"]),
                "subtotal": _fmt2(data["subtotal"]),
                "subtotal_display": _fmt_display(data["subtotal"]),
            }
        )
    return redirect("shop:cart")


@require_POST
def cart_clear_view(request):
    cart_clear(request.session)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "count": 0, "subtotal": "0.00", "subtotal_display": _fmt_display(0)})
    return redirect("shop:cart")


# =========================================================
# PAGES
# =========================================================

@require_GET
def index(request):
    """Home page: category-ordered product grid with optional search (?q=...)."""
    q = (request.GET.get("q") or "").strip()
    sections = _build_sections(request, q)
    return render(
        request,
        "shop/index.html",
        {
            "sections": sections,
            "q": q,
            "is_search": bool(q),
        },
    )


@require_GET
def ajax_search(request):
    """
    AJAX endpoint that returns ONLY the sections HTML fragment.
    Keeps the page static (no reload) while updating results + URL (?q=...).
    """
    q = (request.GET.get("q") or "").strip()
    sections = _build_sections(request, q)
    return render(
        request,
        "shop/partials/sections.html",
        {"sections": sections, "q": q, "is_search": bool(q)},
    )


def product_detail(request, slug=None, pk=None):
    """Localized product detail page (titles/descriptions via ProductTranslation)."""
    ui_short = _short_lang()
    lookup = {"slug": slug} if slug else {"pk": pk}

    base_qs = _prefetch(Product.objects.all())
    product = get_object_or_404(base_qs, **lookup)
    _decorate_product(product, ui_short)

    return render(request, "shop/product_detail.html", {"product": product})
