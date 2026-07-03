import string
import random

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q

from .constants import (
    MAX_LENGTH_EMAIL, 
    MAX_LENGTH_TAG, 
    MAX_LENGTH_NAME, 
    MAX_INGREDIENT_NAME,
    MAX_MEASUREMENT_UNIT,
    SHORT_CODE_LENGTH,
    AMOUNT_MIN,
    AMOUNT_MAX
    )


def generate_short_code(length=6, max_attempts=10):
    chars = string.ascii_lowercase + string.digits
    for _ in range(max_attempts):
        code = ''.join(random.choices(chars, k=length))
        if not Recipe.objects.filter(short_code=code).exists():
            return code
    raise RuntimeError('Не удалось сгенерировать уникальный short_code')


hex_color_validator = RegexValidator(
    regex=r'^#[0-9a-fA-F]{6}$',
    message='Цвет должен быть в формате #RRGGBB',
)


class User(AbstractUser):
    email = models.EmailField(max_length=MAX_LENGTH_EMAIL, unique=True)
    avatar = models.ImageField(upload_to='users/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ('username',)

    def __str__(self):
        return self.username


class Tag(models.Model):
    name = models.CharField(max_length=MAX_LENGTH_TAG, unique=True)
    slug = models.SlugField(max_length=MAX_LENGTH_TAG, unique=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=MAX_INGREDIENT_NAME)
    measurement_unit = models.CharField(max_length=MAX_MEASUREMENT_UNIT)

    class Meta:
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    author = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='recipes'
    )
    name = models.CharField(max_length=MAX_LENGTH_NAME)
    image = models.ImageField(upload_to='recipes/')
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(AMOUNT_MIN, message='Время приготовления должно быть не менее 1 минуты'),
            MaxValueValidator(AMOUNT_MAX, message='Время приготовления не может превышать 32767 минут'),
        ]
    )
    tags = models.ManyToManyField(Tag, related_name='recipes')
    short_code = models.CharField(
        max_length=SHORT_CODE_LENGTH, unique=True, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = generate_short_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        'Recipe', on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        'Ingredient', on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                AMOUNT_MIN,
                message=f'Количество должно быть не менее {AMOUNT_MIN}'
            ),
            MaxValueValidator(
                AMOUNT_MAX,
                message=f'Количество не может превышать {AMOUNT_MAX}'
            ),
        ]
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name} x{self.amount}'


class BaseUserRelation(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        abstract = True
        ordering = ('-created_at',)

    def __str__(self):
        target = getattr(self, 'recipe', None) or getattr(self, 'author', None)
        return f'{self.user} → {target}'


class Favorite(BaseUserRelation):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='favorites'
    )
    recipe = models.ForeignKey(
        'Recipe', on_delete=models.CASCADE, related_name='favorites'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]


class ShoppingCart(BaseUserRelation):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='shopping_carts'
    )
    recipe = models.ForeignKey(
        'Recipe', on_delete=models.CASCADE, related_name='in_carts'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='unique_shopping_cart'
            )
        ]

class Subscription(BaseUserRelation):
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='subscriptions'
    )
    author = models.ForeignKey(
        'User', on_delete=models.CASCADE, related_name='subscribers'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            ),
            models.CheckConstraint(
                check=~Q(user=models.F('author')),
                name='prevent_self_subscription'
            ),
        ]
