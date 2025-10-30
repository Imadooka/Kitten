from django.db import models
from datetime import date, timedelta
from django.core.files.storage import default_storage
from django.conf import settings

class IngredientImage(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='ingredient_images/')

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=1)
    image = models.ForeignKey(
        IngredientImage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingredients"
    )
    prepared_date = models.DateField(default=date.today)
    shelf_life_days = models.PositiveIntegerField(default=7)
    expiry_date = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
    # ถ้าไม่ได้กำหนด expiry_date ให้คำนวณจาก prepared_date + shelf_life_days
        if not self.expiry_date and self.prepared_date:
            self.expiry_date = self.prepared_date + timedelta(days=self.shelf_life_days)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    @property
    def computed_expiry(self):
        if self.expiry_date:
            return self.expiry_date
        pd = self.prepared_date or date.today()
        return pd + timedelta(days=self.shelf_life_days or 0)

    @property
    def days_remaining(self):
        # ใช้ computed_expiry เพื่อกัน None
        return (self.computed_expiry - date.today()).days


    @property
    def image_url(self):
        """
        ลำดับ:
        1) ถ้ามีรูปที่ผูกกับรายการและไฟล์อยู่จริง -> ใช้ไฟล์นั้น
        2) ถ้าไม่มี/ไฟล์หาย -> หา IngredientImage ที่ชื่อเดียวกันและไฟล์อยู่จริง
        3) ถ้าใน media มี default.png -> ใช้ default
        4) ไม่งั้นคืนค่าว่าง
        """
        # 1) รูปที่ผูกกับรายการ
        if self.image and getattr(self.image, "image", None):
            f = self.image.image
            if getattr(f, "name", "") and default_storage.exists(f.name):
                return f.url

        # 2) หาโดยชื่อวัตถุดิบ
        img = IngredientImage.objects.filter(name=self.name).first()
        if img and img.image and getattr(img.image, "name", "") and default_storage.exists(img.image.name):
            return img.image.url

        # 3) default ใน media
        default_rel = "ingredient_images/default.png"
        if default_storage.exists(default_rel):
            return settings.MEDIA_URL + default_rel

        # 4) ไม่มีรูป
        return ""
    
    ingredient_map = {
    "มะเขือเทศ": "tomato",
    "หมู": "pork",
    "ไก่": "chicken",
    "ไข่": "egg",
    "กะเพรา": "basil"
}
