from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .fields import Base64ImageField
from recipes.models import (
    Ingredient, Recipe, RecipeIngredient, Tag
)
from users.models import Subscription


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
        return ""


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient'
    )
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
        return bool(
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        )

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

    def get_recipes(self, obj):
        recipes_limit = 3
        request = self.context.get('request')
        if request:
            try:
                recipes_limit = int(
                    request.query_params.get('recipes_limit', recipes_limit)
                )
            except (ValueError, TypeError):
                pass
        recipes = obj.recipes.all()[:recipes_limit]
        return RecipeMinifiedSerializer(
            recipes, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField()

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and ret.get('avatar'):
            ret['avatar'] = request.build_absolute_uri(ret['avatar'])
        return ret


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
        return ""


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
        ingredients = data.get('ingredients')
        ingredient_ids = [item['ingredient'].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться'}
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
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags_data)
        instance.recipe_ingredients.all().delete()
        self._create_ingredients(instance, ingredients_data)
        return instance

    def _create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['ingredient'].pk,
                amount=item['amount'],
            )
            for item in ingredients_data
        )

    def to_representation(self, instance):
        return RecipeListSerializer(instance, context=self.context).data
