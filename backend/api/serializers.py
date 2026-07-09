from django.db import transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .fields import Base64ImageField
from recipes.models import (
    Ingredient, Recipe, RecipeIngredient, Tag
)
from .models import Subscription


User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        if obj.image and obj.image.url:
            return obj.image.url
        return None


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class ExtendedUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj:
            return Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False

    def get_avatar(self, obj):
        if obj.avatar and obj.avatar.url:
            return obj.avatar.url
        return None


class UserWithRecipesSerializer(ExtendedUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes',
            'recipes_count', 'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False

    def get_recipes(self, obj):
        recipes_limit = self.context.get('recipes_limit', 3)
        recipes = obj.recipes.all()[:recipes_limit]
        return RecipeMinifiedSerializer(
            recipes, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField()


class RecipeListSerializer(serializers.ModelSerializer):
    author = ExtendedUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True, source='recipe_ingredients', read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True, default=False
    )
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time',
        )

    def get_image(self, obj):
        if obj.image and obj.image.url:
            return obj.image.url
        return None


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = IngredientInRecipeSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image',
            'name', 'text', 'cooking_time',
        )

    def validate(self, data):
        if not data.get('tags'):
            raise serializers.ValidationError(
                {'tags': 'Нужно указать хотя бы один тег'}
            )
        if not data.get('ingredients'):
            raise serializers.ValidationError(
                {'ingredients': 'Нужно указать хотя бы один ингредиент'}
            )
        tags = data.get('tags')
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться'}
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(
            **validated_data, author=self.context['request'].user
        )
        recipe.tags.set(tags_data)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        if tags_data is not None:
            instance.tags.clear()
            instance.tags.set(tags_data)
        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            self._create_ingredients(instance, ingredients_data)
        return instance

    def _create_ingredients(self, recipe, ingredients_data):
        seen = set()
        for item in ingredients_data:
            ingredient_id = item['id'].pk
            if ingredient_id in seen:
                raise serializers.ValidationError(
                    {'ingredients': f'Ингредиент с id {ingredient_id} указан '
                                    f'более одного раза'}
                )
            seen.add(ingredient_id)
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['id'].pk,
                amount=item['amount'],
            )
            for item in ingredients_data
        )

    def to_representation(self, instance):
        return RecipeListSerializer(instance, context=self.context).data
