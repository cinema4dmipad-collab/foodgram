from django_filters.rest_framework import (
    FilterSet, BooleanFilter, CharFilter, ModelMultipleChoiceFilter
)

from recipes.models import Ingredient, Recipe, Tag


class IngredientFilter(FilterSet):
    name = CharFilter(method='filter_name')

    class Meta:
        model = Ingredient
        fields = ['name']

    def filter_name(self, queryset, name, value):
        if value:
            return queryset.filter(name__istartswith=value)
        return queryset


class RecipeFilter(FilterSet):
    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug', queryset=Tag.objects.all(),
        to_field_name='slug'
    )
    is_favorited = BooleanFilter(field_name='is_favorited')
    is_in_shopping_cart = BooleanFilter(field_name='is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']
