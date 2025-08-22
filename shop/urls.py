from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    # Choose one depending on whether you have a slug:
    path("p/<slug:slug>/", views.product_detail, name="product_detail"),
    path("p/id/<int:pk>/", views.product_detail, name="product_detail_by_id"),
]
