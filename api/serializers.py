from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Recipe, FavoriteRecipe, CommunityRecipe

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        return user

class RecipeSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source="author.username")

    class Meta:
        model = Recipe
        fields = "__all__"
        read_only_fields = ("author", "is_ai_generated", "created_at")


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)
    recipe_id = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(), source="recipe", write_only=True
    )

    class Meta:
        model = FavoriteRecipe
        fields = ("id", "recipe", "recipe_id", "created_at")

class GenerateRecipeInputSerializer(serializers.Serializer):
    ingredients = serializers.ListField(
        child=serializers.CharField(), min_length=1
    )
    cooking_method = serializers.CharField(
        required=False, allow_blank=True
    )  # ví dụ: "chiên", "nướng", "hấp"
    cuisine = serializers.CharField(
        required=False, allow_blank=True
    )  # ví dụ: "Việt Nam", "Hàn Quốc", "Miền Trung"