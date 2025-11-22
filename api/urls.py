# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    RegisterView,
    me_view,
    RecipeViewSet,
    favorite_view,
    generate_recipe_view,
)

router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")

urlpatterns = [
    # Auth
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", me_view, name="auth-me"),

    # AI Generate
    path("recipes/generate/", generate_recipe_view, name="recipe-generate"),

    # Favorites
    path("favorites/", favorite_view, name="favorites"),

    # Recipes CRUD (router)
    path("", include(router.urls)),
]
