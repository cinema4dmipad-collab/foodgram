import io
import json
import os
from random import randint

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from api.models import User


class Command(BaseCommand):
    help = 'Creates test users with recipes from data/test_data.json'

    def handle(self, *args, **options):
        json_path = os.path.join(
            settings.BASE_DIR.parent, 'data', 'test_data.json'
        )
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            users_data = json.load(f)

        for user_data in users_data:
            recipes_data = user_data.pop('recipes')
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data,
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  Created user: {user.username}')
            else:
                self.stdout.write(f'  Skipped existing user: {user.username}')

            for recipe_data in recipes_data:
                self._create_recipe(user, recipe_data)

        self.stdout.write(self.style.SUCCESS('Test data loaded'))

    def _create_recipe(self, author, recipe_data):
        tag_slugs = recipe_data.pop('tags')
        ingredients_data = recipe_data.pop('ingredients')

        recipe, created = Recipe.objects.get_or_create(
            author=author,
            name=recipe_data['name'],
            defaults={
                **recipe_data,
                'image': self._make_placeholder_image(),
            },
        )
        if not created:
            self.stdout.write(f'    Skipped existing recipe: {recipe.name}')
            return

        recipe.tags.set(
            Tag.objects.filter(slug__in=tag_slugs)
        )

        for item in ingredients_data:
            ingredient = Ingredient.objects.filter(
                name=item['name']
            ).first()
            if not ingredient:
                self.stdout.write(self.style.WARNING(
                    f'      Ingredient not found: {item["name"]}'
                ))
                continue
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=item['amount'],
            )

        self.stdout.write(f'    Created recipe: {recipe.name}')

    @staticmethod
    def _make_placeholder_image():
        img = Image.new('RGB', (800, 600), (
            randint(50, 200), randint(50, 200), randint(50, 200),
        ))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return ContentFile(buffer.getvalue(), name='placeholder.png')
