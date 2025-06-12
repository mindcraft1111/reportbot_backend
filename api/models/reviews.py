from django.db import models
from .utils.soft_delete import SoftDeleteMixin


class ProductCategory(models.TextChoices):
    SKINCARE = ("SKIN", "스킨케어")
    MAKEUP = ("MAKE", "메이크업")
    HAIRCARE = ("HAIR", "헤어케어")
    PET = ("PET", "반려동물")
    LIFESTYLE = ("LIFE", "생활용품")
    ELECTRONICS = ("ELEC", "전자기기")
    CAR_ACCESSORY = ("CAR", "차량용품")
    ETC = ("ETC", "기타")


class Products(SoftDeleteMixin):
    category = models.CharField(max_length=100, choices=ProductCategory.choices, null=True, verbose_name="카테고리")
    product_name = models.CharField(max_length=200, blank=False, null=False, verbose_name="제품명")
    brand = models.CharField(max_length=100, blank=False, null=False, verbose_name="브랜드명")
    price = models.PositiveIntegerField(blank=False, null=False, verbose_name="가격")
    discount_rate = models.PositiveIntegerField(blank=True, null=True, verbose_name="할인율")

    class Meta:
        db_table = "products"
    
    def __str__(self):
        return f"[{self.brand}] {self.product_name[:10]}"


class Reviews(SoftDeleteMixin):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(blank=False, null=False, verbose_name="평점")
    review = models.TextField(blank=True, null=True, verbose_name="내용")
    review_date = models.CharField(max_length=100, verbose_name="작성일자")

    class Meta:
        db_table = "reviews"
    
    def __str__(self):
        return f"[{self.product.product_name[:5]}..] 리뷰: {self.review[:10]}"
