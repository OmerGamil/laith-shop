from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    # Choose one depending on whether you have a slug:
    path("p/<slug:slug>/", views.product_detail, name="product_detail"),
    path("p/id/<int:pk>/", views.product_detail, name="product_detail_by_id"),
    path("ajax/search/", views.ajax_search, name="ajax_search"),
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/", views.cart_add_view, name="cart_add"),
    path("cart/update/", views.cart_update_qty_view, name="cart_update"),
    path("cart/remove/", views.cart_remove_view, name="cart_remove"),
    path("cart/clear/", views.cart_clear_view, name="cart_clear"),
]
