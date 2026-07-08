from rest_framework.pagination import PageNumberPagination
from django.conf import settings


class LimitPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = settings.PAGE_SIZE
    max_page_size = settings.MAX_PAGE_SIZE
