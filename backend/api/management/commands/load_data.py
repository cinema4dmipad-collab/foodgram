import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Ingredient, Tag

TAGS = [
    {'name': 'Завтрак', 'color': '#E26C2D', 'slug': 'breakfast'},
    {'name': 'Обед', 'color': '#49B24E', 'slug': 'lunch'},
    {'name': 'Ужин', 'color': '#8775D2', 'slug': 'dinner'},
]


class Command(BaseCommand):
    help = 'Loads ingredients from data/ingredients.json and creates tags'

    def handle(self, *args, **options):
        for tag_data in TAGS:
            Tag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults=tag_data,
            )
        self.stdout.write(self.style.SUCCESS('Tags loaded'))

        json_path = os.path.join(
            settings.BASE_DIR.parent, 'data', 'ingredients.json'
        )
        if not os.path.exists(json_path):
            self.stdout.write(
                self.style.WARNING(
                    f'File not found: {json_path}'
                )
            )
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            ingredients = json.load(f)

        created = 0
        for item in ingredients:
            _, was_created = Ingredient.objects.get_or_create(
                name=item['name'],
                measurement_unit=item['measurement_unit'],
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Ingredients loaded: {created} created, '
                f'{len(ingredients) - created} already exist'
            )
        )
