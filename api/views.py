from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .serializers import RegisterSerializer, FavoriteSerializer, RecipeSerializer

# Create your views here.
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
    })


from rest_framework import viewsets, permissions, status
from .models import Recipe, FavoriteRecipe

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by("-created_at")
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def favorite_view(request):
    user = request.user

    if request.method == "GET":
        qs = FavoriteRecipe.objects.filter(user=user).select_related("recipe")
        serializer = FavoriteSerializer(qs, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = FavoriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.validated_data["recipe"]
        fav, created = FavoriteRecipe.objects.get_or_create(user=user, recipe=recipe)
        return Response(FavoriteSerializer(fav).data, status=status.HTTP_201_CREATED)

    if request.method == "DELETE":
        recipe_id = request.data.get("recipe_id")
        FavoriteRecipe.objects.filter(user=user, recipe_id=recipe_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

from .genai_service import generate_recipe_from_genai
from .serializers import (
    RecipeSerializer,
    FavoriteSerializer,
    GenerateRecipeInputSerializer,
)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])  # cần login
def generate_recipe_view(request):
    """
    Body:
    {
      "ingredients": ["trứng", "cà chua", "hành lá"],
      "cooking_method": "chiên",
      "cuisine": "Việt Nam"
    }
    """
    serializer = GenerateRecipeInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    ingredients = serializer.validated_data["ingredients"]
    cooking_method = serializer.validated_data.get("cooking_method") or None
    cuisine = serializer.validated_data.get("cuisine") or None

    try:
        gen_data = generate_recipe_from_genai(
            ingredients,
            cooking_method=cooking_method,
            cuisine=cuisine,
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Map data từ GenAI sang model Recipe
    title = gen_data.get("title", "Món ăn gợi ý")
    description = gen_data.get("description", "")
    ingredients_text = "\n".join(gen_data.get("ingredients", []))
    steps_list = gen_data.get("steps", [])
    steps_text = "\n".join(steps_list)

    # Lưu vào DB (is_ai_generated=True)
    recipe = Recipe.objects.create(
        title=title,
        description=description,
        ingredients_text=ingredients_text,
        steps=steps_text,
        image_url="",  # sau này có thể thêm GenAI image
        is_ai_generated=True,
        author=request.user,
    )

    recipe_data = RecipeSerializer(recipe).data
    # có thể trả thêm raw gen_data nếu muốn
    return Response(
        {
            "success": True,
            "data": recipe_data,
            "raw": gen_data,
        },
        status=status.HTTP_201_CREATED,
    )