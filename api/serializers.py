# api/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Recipe, FavoriteRecipe


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
    """
    - FE gửi / nhận: ingredients: string[], steps: string[], nutrition: {…}
    - DB lưu: ingredients_text, steps (TextField), nutrition (JSONField)
    """
    ingredients = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )
    steps = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )
    nutrition = serializers.DictField(
        child=serializers.CharField(),
        required=False,
    )
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "title",
            "description",
            "ingredients",
            "steps",
            "cooking_method",
            "cuisine",
            "nutrition",
            "image_url",
            "is_ai_generated",
            "author",
            "created_at",
        )
        read_only_fields = ("is_ai_generated", "author", "created_at")

    # Convert từ model -> JSON cho FE
    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["ingredients"] = (
            instance.ingredients_text.splitlines() if instance.ingredients_text else []
        )
        data["steps"] = instance.steps.splitlines() if instance.steps else []

        nutr = instance.nutrition or {}
        data["nutrition"] = {
            "calories": str(nutr.get("calories", "")),
            "protein": str(nutr.get("protein", "")),
            "fat": str(nutr.get("fat", "")),
            "carbs": str(nutr.get("carbs", "")),
        }
        return data

    # Create từ JSON -> model
    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients", [])
        steps = validated_data.pop("steps", [])
        nutrition = validated_data.pop("nutrition", {})

        recipe = Recipe.objects.create(
            ingredients_text="\n".join(ingredients),
            steps="\n".join(steps),
            nutrition=nutrition,
            **validated_data,
        )
        return recipe

    # Update
    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        steps = validated_data.pop("steps", None)
        nutrition = validated_data.pop("nutrition", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if ingredients is not None:
            instance.ingredients_text = "\n".join(ingredients)
        if steps is not None:
            instance.steps = "\n".join(steps)
        if nutrition is not None:
            instance.nutrition = nutrition

        instance.save()
        return instance


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)
    recipe_id = serializers.PrimaryKeyRelatedField(
        source="recipe",
        queryset=Recipe.objects.all(),
        write_only=True,
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
