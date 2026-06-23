import binascii
import base64
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                format, imgstr = data.split(';base64,')
            except ValueError:
                raise serializers.ValidationError(
                    'Неверный формат base64 изображения'
                )
            ext = format.split('/')[-1]
            if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                ext = 'png'
            try:
                decoded = base64.b64decode(imgstr)
            except (binascii.Error, ValueError):
                raise serializers.ValidationError(
                    'Не удалось декодировать base64 изображение'
                )
            data = ContentFile(
                decoded,
                name=f'{uuid.uuid4()}.{ext}'
            )
        return super().to_internal_value(data)
