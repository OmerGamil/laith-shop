# views.py
import re
from django.db.models import Q, Prefetch
from django.shortcuts import render, get_object_or_404
from django.utils.translation import get_language, gettext as _

from .models import Product, ProductTranslation  # Category translations are name_de/name_ar on Category

# --- helpers from earlier (unchanged) ---
def _cat_display_title(cat, ui_short):
    name_de = getattr(cat, "name_de", None)
    name_ar = getattr(cat, "name_ar", None)
    generic = getattr(cat, "name", None) or getattr(cat, "title", None) or str(cat)
    if ui_short == "ar":
        return (name_ar or name_de or generic)
    return (name_de or generic or name_ar)

def _pick_translation(tr_list, ui_lang_short, default_lang_short="de"):
    if not tr_list: return None
    preferred = ["ar", default_lang_short] if ui_lang_short == "ar" else [ui_lang_short, default_lang_short]
    def lang_of(t):
        return (getattr(t, "language_code", None) or getattr(t, "language", "")).lower().split("-")[0]
    for want in preferred:
        for t in tr_list:
            if lang_of(t) == want:
                return t
    return tr_list[0]

def _with_display_fields(qs, default_lang="de"):
    ui_short = (get_language() or default_lang).lower().split("-")[0]
    qs = (
        qs.select_related("category")
          .prefetch_related(Prefetch("translations", queryset=ProductTranslation.objects.all(), to_attr="tr_list"))
    )
    for p in qs:
        # product title/description (from ProductTranslation)
        tr = _pick_translation(getattr(p, "tr_list", []), ui_short, default_lang)
        raw_title = getattr(p, "slug", None) or str(p)   # <- no p.title/name – they don't exist
        raw_desc  = ""                                   # base model has no description
        p.display_title = (getattr(tr, "title", None) or raw_title) if tr else raw_title
        p.display_description = (getattr(tr, "description", None) or raw_desc) if tr else raw_desc
        p.category_display_title = _cat_display_title(getattr(p, "category", None), ui_short) if getattr(p, "category", None) else None
    return qs
# --- end helpers ---

def index(request):
    q = (request.GET.get("q") or "").strip()

    qs = Product.objects.all().order_by("-id")

    # Language-agnostic search: match ANY translation (AR/DE) + raw fields
    if q:
        terms = [t for t in re.split(r"\s+", q) if t]

        # Only use fields that EXIST on your models
        SEARCH_FIELDS = (
            "translations__title__icontains",
            "translations__description__icontains",
            "slug__icontains",   # exists on Product
            "sku__icontains",    # exists on Product
        )

        for term in terms:
            term_q = Q()
            for f in SEARCH_FIELDS:
                term_q |= Q(**{f: term})
            qs = qs.filter(term_q)

        qs = qs.distinct()

    products = _with_display_fields(qs)

    # Group by *stable* anchor so RTL/Arabic labels don’t break IDs
    grouped = {}
    for p in products:
        if getattr(p, "category", None):
            anchor = f"cat-{p.category.pk}"
            label = p.category_display_title
        else:
            anchor = "cat-misc"
            label = _("Sonstiges")
        bucket = grouped.setdefault(anchor, {"anchor": anchor, "label": label, "products": []})
        bucket["products"].append(p)

    sections = sorted(grouped.values(), key=lambda s: s["label"].lower())
    return render(request, "shop/index.html", {
        "sections": sections,
        "q": q,
        "is_search": bool(q),
    })


def product_detail(request, slug=None, pk=None):
    lookup = {"slug": slug} if slug else {"pk": pk}
    product = get_object_or_404(Product, **lookup)
    _with_display_fields([product])
    return render(request, "shop/product_detail.html", {"product": product})
