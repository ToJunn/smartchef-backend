from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ingredients_text = models.TextField()  # lưu text list nguyên liệu
    steps = models.TextField()
    image_url = models.URLField(blank=True)
    is_ai_generated = models.BooleanField(default=False)
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recipes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "recipe")


class CommunityRecipe(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()      # mô tả / steps
    ingredients_text = models.TextField()
    image_url = models.URLField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_recipes")
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
