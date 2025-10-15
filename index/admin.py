from django.contrib import admin
from django.utils.html import format_html
from .models import Ingredient, IngredientImage

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'prepared_date', 'shelf_life_days', 'expiry_date', 'days_remaining', 'image_attached')
    search_fields = ('name',)
    list_filter = ('prepared_date',)

    def image_attached(self, obj):
        return "✔" if obj.image_url else "—"
    image_attached.short_description = "Image?"

@admin.register(IngredientImage)
class IngredientImageAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_preview')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:6px;" />', obj.image.url)
        return 'ไม่มีรูป'
    image_preview.short_description = 'Preview'
