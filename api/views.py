# api/views.py
from django.contrib.auth.models import User

from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Recipe, FavoriteRecipe
from .serializers import (
    RegisterSerializer,
    RecipeSerializer,
    FavoriteRecipeSerializer,
    GenerateRecipeInputSerializer,
)
from .genai_service import generate_recipe


# ==========================
#  AUTH
# ==========================

class RegisterView(generics.CreateAPIView):
    """
    Đăng ký tài khoản mới.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    """
    Trả về thông tin user đang đăng nhập.
    """
    user = request.user
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )


# ==========================
#  RECIPE CRUD
# ==========================

class RecipeViewSet(viewsets.ModelViewSet):
    """
    CRUD cho Recipe.
    - Ai cũng xem được (GET).
    - Chỉ user đã đăng nhập mới tạo / sửa / xoá.
    """
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Recipe.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# ==========================
#  FAVORITES
# ==========================

@api_view(["GET", "POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def favorite_view(request):
    """
    GET    /api/favorites/           -> list các recipe user đã yêu thích
    POST   /api/favorites/           -> body: { "recipe_id": <id> } -> thêm/tạo favorite
    DELETE /api/favorites/           -> body: { "recipe_id": <id> } -> bỏ favorite
    """
    user = request.user

    if request.method == "GET":
        favorites = FavoriteRecipe.objects.filter(user=user).select_related("recipe")
        serializer = FavoriteRecipeSerializer(favorites, many=True)
        return Response(serializer.data)

    recipe_id = request.data.get("recipe_id")
    if not recipe_id:
        return Response(
            {"detail": "recipe_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        recipe = Recipe.objects.get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return Response(
            {"detail": "Recipe not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "POST":
        fav, created = FavoriteRecipe.objects.get_or_create(
            user=user, recipe=recipe
        )
        return Response({"is_favorite": True}, status=status.HTTP_201_CREATED)

    if request.method == "DELETE":
        FavoriteRecipe.objects.filter(user=user, recipe=recipe).delete()
        return Response({"is_favorite": False}, status=status.HTTP_204_NO_CONTENT)


# ==========================
#  GENERATE RECIPE (AI)
# ==========================

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])  # bắt buộc login
def generate_recipe_view(request):
    """
    Sinh công thức món ăn từ nguyên liệu + (cách nấu, ẩm thực).
    Body:
    {
      "ingredients": ["trứng", "cà chua"],
      "cooking_method": "chiên",
      "cuisine": "Việt Nam"
    }

    Trả về trực tiếp 1 Recipe (JSON) sau khi lưu vào DB.
    """
    input_serializer = GenerateRecipeInputSerializer(data=request.data)
    input_serializer.is_valid(raise_exception=True)
    payload = input_serializer.validated_data

    gen_data = generate_recipe(
        ingredients=payload["ingredients"],
        cooking_method=payload.get("cooking_method"),
        cuisine=payload.get("cuisine"),
    )

    # Lưu vào DB
    recipe = Recipe.objects.create(
        title=gen_data["title"],
        description=gen_data.get("description", ""),
        ingredients_text="\n".join(gen_data.get("ingredients", [])),
        steps="\n".join(gen_data.get("steps", [])),
        cooking_method=gen_data.get("cooking_method") or "",
        cuisine=gen_data.get("cuisine") or "",
        image_url="",
        is_ai_generated=True,
        nutrition=gen_data.get("nutrition", {}),
        author=request.user,
    )

    recipe_data = RecipeSerializer(recipe).data
    return Response(recipe_data, status=status.HTTP_201_CREATED)
