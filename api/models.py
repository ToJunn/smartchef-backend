# api/models.py
from django.db import models
from django.contrib.auth.models import User


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Recipe(models.Model):
    """
    Bài post công thức món ăn (cả user tạo & AI generate).
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Lưu dạng text, mỗi dòng 1 nguyên liệu / bước,
    # Serializer sẽ convert thành list[str] cho FE.
    ingredients_text = models.TextField()
    steps = models.TextField()

    cooking_method = models.CharField(max_length=100, blank=True)
    cuisine = models.CharField(max_length=100, blank=True)

    image_url = models.URLField(blank=True)

    # Công thức này do AI gợi ý hay user tự tạo
    is_ai_generated = models.BooleanField(default=False)

    # Nutrition dạng JSON: {calories, protein, fat, carbs}
    nutrition = models.JSONField(default=dict, blank=True)

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class FavoriteRecipe(models.Model):
    """
    Một recipe được user yêu thích.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_recipes",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "recipe")

    def __str__(self) -> str:
        return f"{self.user.username} ❤️ {self.recipe.title}"
