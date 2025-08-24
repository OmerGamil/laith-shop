from .cart import totals as cart_totals
from .models import Product

def cart(request):
    try:
        data = cart_totals(request.session, Product)
        count = sum(li["qty"] for li in data["lines"])
        subtotal = data["subtotal"]
    except Exception:
        count, subtotal = 0, 0
    return {"cart_count": count, "cart_subtotal": subtotal}
