from django import forms
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from django_summernote.admin import SummernoteModelAdmin, SummernoteInlineModelAdmin

from .models import Category, Product, ProductTranslation, translate_text


# --- Inlines ---
class ProductTranslationInline(SummernoteInlineModelAdmin, admin.StackedInline):
    model = ProductTranslation
    extra = 0
    max_num = 2
    fields = ("language", "title", "description")
    summernote_fields = ("description",)  # rich text editor


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ("sku", "price", "sale_price", "stock", "is_active")
    show_change_link = True


# --- Product Admin ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "title_de",
        "title_ar",
        "category",
        "price",
        "sale_price",
        "stock",
        "is_active",
        "slug",
        "thumb",
    )
    list_filter = ("category", "is_active")
    search_fields = (
        "sku",
        "translations__title",
        "translations__description",
        "category__name_de",
        "category__name_ar",
    )
    list_select_related = ("category",)
    autocomplete_fields = ("category",)
    inlines = [ProductTranslationInline]
    readonly_fields = ("slug", "created_at", "updated_at", "image_preview")
    fieldsets = (
        (None, {"fields": ("category", "sku", "slug")}),
        ("Pricing", {"fields": ("price", "sale_price")}),
        ("Inventory", {"fields": ("stock", "is_active")}),
        ("Media", {"fields": ("image", "image_preview")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Title (DE)")
    def title_de(self, obj):
        tr = obj.translations.filter(language="de").first()
        return tr.title if tr else "-"

    @admin.display(description="Title (AR)")
    def title_ar(self, obj):
        tr = obj.translations.filter(language="ar").first()
        return tr.title if tr else "-"

    @admin.display(description="Image")
    def thumb(self, obj):
        if getattr(obj, "image", None):
            try:
                return format_html(
                    '<img src="{}" style="height:50px;border-radius:4px;object-fit:cover;" />',
                    obj.image.url,
                )
            except Exception:
                return "-"
        return "-"

    @admin.display(description="Preview")
    def image_preview(self, obj):
        return self.thumb(obj)


# --- Category Admin ---
class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow entering only German OR only Arabic; we'll translate the other
        self.fields["name_ar"].required = False
        self.fields["name_de"].required = False

    def clean(self):
        cleaned = super().clean()
        name_ar = cleaned.get("name_ar")
        name_de = cleaned.get("name_de")
        if not name_ar and not name_de:
            raise forms.ValidationError("Please provide at least a German or Arabic name.")
        return cleaned


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ("name_de", "name_ar", "slug", "product_count")
    search_fields = ("name_de", "name_ar")
    prepopulated_fields = {"slug": ("name_de",)}  # UI hint; model still enforces German-based slug
    inlines = [ProductInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_product_count=Count("products"))

    @admin.display(description="Products", ordering="_product_count")
    def product_count(self, obj):
        return getattr(obj, "_product_count", None) or obj.products.count()

    def save_model(self, request, obj, form, change):
        # Translate in admin before save for immediate feedback
        if obj.name_de and not obj.name_ar:
            obj.name_ar = translate_text(obj.name_de, target_lang="ar", source_lang="de")
        elif obj.name_ar and not obj.name_de:
            obj.name_de = translate_text(obj.name_ar, target_lang="de", source_lang="ar")
        super().save_model(request, obj, form, change)


# --- ProductTranslation Admin ---
@admin.register(ProductTranslation)
class ProductTranslationAdmin(SummernoteModelAdmin):
    list_display = ("product", "language", "title")
    list_filter = ("language",)
    search_fields = ("title", "description", "product__sku")
    summernote_fields = ("description",)
