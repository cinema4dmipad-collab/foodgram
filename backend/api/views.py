from django.db.models import Exists, OuterRef, Sum
from django.db.models.functions import Lower
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from rest_framework import generics
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
)
from rest_framework.permissions import (
    IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Favorite, Ingredient, Recipe, RecipeIngredient,
    ShoppingCart, Subscription, Tag, User,
)
from .pagination import CustomPagination
from .permissions import IsAuthor
from .serializers import (
    AvatarSerializer, IngredientSerializer,
    RecipeCreateSerializer, RecipeListSerializer,
    RecipeMinifiedSerializer, TagSerializer,
    UserWithRecipesSerializer, CustomUserSerializer
)


def redirect_to_recipe(request, code):
    recipe = get_object_or_404(Recipe, short_code=code)
    return redirect(f'/recipes/{recipe.id}/')


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = 'id'


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = 'id'

    def get_queryset(self):
        name = self.request.query_params.get('name', '')
        if name:
            return Ingredient.objects.annotate(
                name_lower=Lower('name')
            ).filter(name_lower__startswith=name.lower())
        return Ingredient.objects.all()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'recipe_ingredients__ingredient'
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update', 'update'):
            return RecipeCreateSerializer
        return RecipeListSerializer

    def get_permissions(self):
        if self.action in ('partial_update', 'update', 'destroy'):
            return [IsAuthenticated(), IsAuthor()]
        return super().get_permissions()

    def perform_create(self, serializer):
        tags = self.request.data.get('tags', [])
        if len(tags) != len(set(tags)):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'tags': 'Теги не должны повторяться'})
        serializer.save(author=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        recipe = get_object_or_404(Recipe, pk=kwargs.get('pk'))
        if recipe.author != request.user:
            return Response(
                {'errors': 'Вы не являетесь автором этого рецепта'},
                status=status.HTTP_403_FORBIDDEN
            )
        tags = request.data.get('tags', [])
        if len(tags) != len(set(tags)):
            return Response(
                {'errors': 'Теги не должны повторяться'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(
            recipe,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def get_queryset(self):
        queryset = super().get_queryset()
        author = self.request.query_params.get('author')
        tags = self.request.query_params.getlist('tags')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )

        if author:
            try:
                author = int(author)
            except (ValueError, TypeError):
                raise ValidationError(
                    {'author': 'Некорректное значение параметра author'}
                )
            queryset = queryset.filter(author_id=author)
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        if is_favorited and self.request.user.is_authenticated:
            queryset = queryset.filter(
                favorites__user=self.request.user
            )
        if is_in_shopping_cart and self.request.user.is_authenticated:
            queryset = queryset.filter(
                shopping_carts__user=self.request.user
            )

        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                _is_favorited=Exists(
                    Favorite.objects.filter(
                        user=self.request.user, recipe=OuterRef('pk')
                    )
                ),
                _is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=self.request.user, recipe=OuterRef('pk')
                    )
                ),
            )
        return queryset

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(
            f'/s/{recipe.short_code}/'
        )
        return Response({'short-link': short_link})

    @action(detail=True, methods=['post'], url_path='favorite')
    def add_favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'errors': 'Рецепт уже в избранном'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Favorite.objects.create(user=user, recipe=recipe)
        serializer = RecipeMinifiedSerializer(
            recipe, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @add_favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        deleted, _ = Favorite.objects.filter(
            user=user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'errors': 'Рецепт не в избранном'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='shopping_cart')
    def add_shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if ShoppingCart.objects.filter(
            user=user, recipe=recipe
        ).exists():
            return Response(
                {'errors': 'Рецепт уже в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ShoppingCart.objects.create(user=user, recipe=recipe)
        serializer = RecipeMinifiedSerializer(
            recipe, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @add_shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        deleted, _ = ShoppingCart.objects.filter(
            user=user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'errors': 'Рецепт не в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='download_shopping_cart',
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        cart_recipes = ShoppingCart.objects.filter(
            user=request.user
        ).values_list('recipe_id', flat=True)
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe_id__in=cart_recipes)
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


class SubscriptionListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserWithRecipesSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return User.objects.filter(
            subscribers__user=self.request.user
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        recipes_limit = self.request.query_params.get('recipes_limit', 3)
        try:
            recipes_limit = int(recipes_limit)
        except (ValueError, TypeError):
            recipes_limit = 3
        context['recipes_limit'] = recipes_limit
        return context


class SubscribeView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, id):
        author = get_object_or_404(User, id=id)
        user = request.user
        if user == author:
            return Response(
                {'errors': 'Нельзя подписаться на себя'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Subscription.objects.filter(
            user=user, author=author
        ).exists():
            return Response(
                {'errors': 'Уже подписан'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Subscription.objects.create(user=user, author=author)
        recipes_limit = request.query_params.get('recipes_limit')
        context = {'request': request}
        if recipes_limit:
            try:
                context['recipes_limit'] = int(recipes_limit)
            except (ValueError, TypeError):
                pass
        serializer = UserWithRecipesSerializer(author, context=context)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        author = get_object_or_404(User, id=id)
        if author == request.user:
            return Response(
                {'errors': 'Нельзя отписаться от самого себя'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = Subscription.objects.filter(
            user=request.user, author=author
        ).delete()
        if not deleted:
            return Response(
                {'errors': 'Не был подписан'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, *args, **kwargs):
        """Обновление рецепта (частичное)"""
        recipe = self.get_object()
        if recipe.author != request.user:
            return Response(
                {'errors': 'Вы не являетесь автором этого рецепта'},
                status=status.HTTP_403_FORBIDDEN
            )
        tags = request.data.get('tags', [])
        if len(tags) != len(set(tags)):
            return Response(
                {'errors': 'Теги не должны повторяться'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(
            recipe,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class AvatarView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        user = request.user
        serializer = AvatarSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user.avatar = serializer.validated_data['avatar']
        user.save()
        return Response(
            {'avatar': request.build_absolute_uri(user.avatar.url)},
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete()
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDetailView(generics.RetrieveAPIView):
    """
    Получение пользователя по ID с его рецептами.
    """
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = []


class UserMeView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
