from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Exists, OuterRef, Sum, Value
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
)
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient,
    ShoppingCart, Tag
)
from users.models import Subscription
from .pagination import LimitPagination
from .serializers import (
    AvatarSerializer, IngredientSerializer,
    RecipeCreateSerializer, RecipeListSerializer,
    RecipeMinifiedSerializer, TagSerializer,
    UserWithRecipesSerializer
)
from .permissions import IsAuthorOrReadOnly

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = 'id'


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = 'id'
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'recipe_ingredients__ingredient'
    )
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    pagination_class = LimitPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            return queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=self.request.user, recipe=OuterRef('pk')
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=self.request.user, recipe=OuterRef('pk')
                    )
                ),
            )
        return queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_in_shopping_cart=Value(False, output_field=BooleanField()),
        )

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update', 'update'):
            return RecipeCreateSerializer
        return RecipeListSerializer

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(
            f'/s/{recipe.short_code}/'
        )
        return Response({'short-link': short_link})

    @action(detail=True, methods=['post'], url_path='favorite',
            permission_classes=(IsAuthenticated,))
    def add_favorite(self, request, pk=None):
        return self._add_relation(
            request, Favorite, 'Рецепт уже в избранном'
        )

    @add_favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self._delete_relation(
            request, Favorite, 'Рецепт не в избранном'
        )

    @action(detail=True, methods=['post'], url_path='shopping_cart',
            permission_classes=(IsAuthenticated,))
    def add_shopping_cart(self, request, pk=None):
        return self._add_relation(
            request, ShoppingCart, 'Рецепт уже в списке покупок'
        )

    @add_shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self._delete_relation(
            request, ShoppingCart, 'Рецепт не в списке покупок'
        )

    def _add_relation(self, request, model, error_exists_msg):
        recipe = self.get_object()
        user = request.user
        _, created = model.objects.get_or_create(
            user=user, recipe=recipe
        )
        if not created:
            return Response(
                {'errors': error_exists_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RecipeMinifiedSerializer(
            recipe, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _delete_relation(self, request, model, error_not_found_msg):
        recipe = self.get_object()
        user = request.user
        deleted, _ = model.objects.filter(
            user=user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'errors': error_not_found_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='download_shopping_cart',
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_carts__user=request.user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        lines = ['Список покупок:\n']
        for item in ingredients:
            lines.append(
                f"{item['ingredient__name']} "
                f"({item['ingredient__measurement_unit']})"
                f" — {item['total_amount']}"
            )
        content = '\n'.join(lines)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping-list.txt"'
        )
        return response


class UserViewSet(DjoserUserViewSet):
    pagination_class = LimitPagination

    def get_permissions(self):
        if self.action == 'me':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='subscriptions',
            permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribers__user=request.user)
        page = self.paginate_queryset(queryset)
        context = self.get_serializer_context()
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context=context
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserWithRecipesSerializer(
            queryset, many=True, context=context
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe',
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id=None):
        author = self.get_object()
        user = request.user
        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на себя'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            _, created = Subscription.objects.get_or_create(
                user=user, author=author
            )
            if not created:
                return Response(
                    {'errors': 'Уже подписан'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = UserWithRecipesSerializer(
                author, context=self.get_serializer_context()
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        deleted, _ = Subscription.objects.filter(
            user=user, author=author
        ).delete()
        if not deleted:
            return Response(
                {'errors': 'Не был подписан'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=(IsAuthenticated,))
    def avatar(self, request):
        user = request.user
        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AvatarSerializer(
            instance=user, data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
