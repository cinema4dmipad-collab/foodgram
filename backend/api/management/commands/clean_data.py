from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Subscription
from recipes.models import Recipe

User = get_user_model()


class Command(BaseCommand):
    help = 'Очищает тестовые данные из базы'

    def handle(self, *args, **options):
        self.stdout.write('Очистка тестовых данных...')
        Subscription.objects.all().delete()
        self.stdout.write('✓ Подписки удалены')
        Recipe.objects.all().delete()
        self.stdout.write('✓ Рецепты удалены')
        User.objects.exclude(is_superuser=True).delete()
        self.stdout.write('✓ Пользователи удалены')
        self.stdout.write('Очистка завершена!')
