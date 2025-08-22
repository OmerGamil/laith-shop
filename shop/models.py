import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from cloudinary.models import CloudinaryField
import deepl

# -------------------------
# DeepL setup (unchanged)
# -------------------------
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
_deepl_translator = None
if DEEPL_API_KEY:
    try:
        _deepl_translator = deepl.Translator(DEEPL_API_KEY)
    except Exception:
        _deepl_translator = None  # fail gracefully


def translate_text(text: str, target_lang: str, source_lang: str | None = None) -> str:
    """
    Translate text using DeepL. Works AR <-> DE.
    Falls back to original text on any failure.
    """
    if not text:
        return ""
    if _deepl_translator is None:
        return text

    t = target_lang.upper()[:2]   # 'de' -> 'DE', 'ar' -> 'AR'
    s = source_lang.upper()[:2] if source_lang else None
    try:
        result = _deepl_translator.translate_text(text, target_lang=t, source_lang=s)
        return str(result)
    except Exception:
        return text


# -------------------------
# Slug helper (new)
# -------------------------
def unique_slug_for(model, base: str, *, pk=None, field_name: str = "slug", max_length: int | None = None) -> str:
    # Determine max_length from the model field if not provided
    if max_length is None:
        max_length = model._meta.get_field(field_name).max_length or 255

    base_slug = slugify(base or "") or "item"
    base_slug = base_slug[:max_length]  # initial trim

    qs = model.objects.all()
    if pk:
        qs = qs.exclude(pk=pk)

    slug = base_slug
    if not qs.filter(**{field_name: slug}).exists():
        return slug

    # Deduplicate with -2, -3, ... while keeping length ≤ max_length
    i = 2
    while True:
        suffix = f"-{i}"
        allowed = max_length - len(suffix)
        slug = (base_slug[:allowed] if len(base_slug) > allowed else base_slug) + suffix
        if not qs.filter(**{field_name: slug}).exists():
            return slug
        i += 1


# -------------------------
# Models
# -------------------------
class Category(models.Model):
    name_ar = models.CharField(
        max_length=255,
        verbose_name=_("Name (Arabic)"),
        blank=True,              # <-- add this
    )
    name_de = models.CharField(
        max_length=255,
        blank=True, null=True,   # keep as you had
        verbose_name=_("Name (German)")
    )
    slug = models.SlugField(max_length=160, unique=True, blank=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name_de or self.name_ar or str(self.pk)

    def save(self, *args, **kwargs):
        # keep both names filled using DeepL (both ways)
        if self.name_ar and not self.name_de:
            self.name_de = translate_text(self.name_ar, target_lang="de", source_lang="ar")
        elif self.name_de and not self.name_ar:
            self.name_ar = translate_text(self.name_de, target_lang="ar", source_lang="de")

        # slug MUST be based on German name
        if not self.slug and self.name_de:
            self.slug = unique_slug_for(Category, self.name_de, pk=self.pk)

        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    sku = models.CharField(max_length=50, unique=True, verbose_name=_("SKU"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"))
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name=_("Sale Price"))
    stock = models.PositiveIntegerField(default=0, verbose_name=_("Stock"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    image = CloudinaryField("image", folder="products", blank=True, null=True)
    slug = models.SlugField(max_length=160,unique=True, blank=True)  # NEW
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        tr_de = self.translations.filter(language="de").first()
        tr_ar = self.translations.filter(language="ar").first()
        return (tr_de.title if tr_de else (tr_ar.title if tr_ar else self.sku))

    def save(self, *args, **kwargs):
        """
        Save normally; then (if slug missing) try to set slug from German title.
        This plays nicely with admin inlines where translations save after product.
        """
        new_instance = self.pk is None
        super().save(*args, **kwargs)

        if not self.slug:
            tr_de = self.translations.filter(language="de").first()
            if tr_de and tr_de.title:
                new_slug = unique_slug_for(Product, tr_de.title, pk=self.pk)
                # update only the slug to avoid messing with timestamps
                Product.objects.filter(pk=self.pk).update(slug=new_slug)
                self.slug = new_slug  # keep in-memory object in sync


class ProductTranslation(models.Model):
    LANG_CHOICES = (
        ("ar", _("Arabic")),
        ("de", _("German")),
    )
    product = models.ForeignKey(Product, related_name="translations", on_delete=models.CASCADE)
    language = models.CharField(max_length=2, choices=LANG_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("product", "language")
        verbose_name = _("Product Translation")
        verbose_name_plural = _("Product Translations")

    def __str__(self):
        return f"{self.title} ({self.language})"

    def save(self, *args, **kwargs):
        """
        When saving AR, create DE if missing.
        When saving DE, create AR if missing.
        Uses DeepL to translate title & description.
        """
        super().save(*args, **kwargs)  # save current translation first

        # Only create the counterpart if it doesn't exist
        if self.language == "ar":
            if not self.product.translations.filter(language="de").exists():
                ProductTranslation.objects.create(
                    product=self.product,
                    language="de",
                    title=translate_text(self.title, target_lang="de", source_lang="ar"),
                    description=translate_text(self.description or "", target_lang="de", source_lang="ar"),
                )
        elif self.language == "de":
            if not self.product.translations.filter(language="ar").exists():
                ProductTranslation.objects.create(
                    product=self.product,
                    language="ar",
                    title=translate_text(self.title, target_lang="ar", source_lang="de"),
                    description=translate_text(self.description or "", target_lang="ar", source_lang="de"),
                )


# -------------------------
# Signals
# -------------------------
@receiver(post_save, sender=ProductTranslation)
def set_product_slug_on_de_change(sender, instance, **kwargs):
    if instance.language != "de":
        return
    product = instance.product
    new_slug = unique_slug_for(Product, instance.title, pk=product.pk)  # max length auto-respected
    if product.slug != new_slug:
        Product.objects.filter(pk=product.pk).update(slug=new_slug)


@receiver(post_delete, sender=Product)
def auto_delete_cloudinary_image_on_delete(sender, instance, **kwargs):
    """Clean up Cloudinary asset when a product is deleted."""
    if getattr(instance, "image", None):
        try:
            instance.image.delete(save=False)
        except Exception:
            pass
