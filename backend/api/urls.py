from django.urls import path, include
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('recipes', views.RecipeViewSet, basename='recipes')
router.register('tags', views.TagViewSet, basename='tags')
router.register('ingredients', views.IngredientViewSet, basename='ingredients')

urlpatterns = [
    path('users/subscriptions/', views.SubscriptionListView.as_view()),
    path('users/<int:id>/subscribe/', views.SubscribeView.as_view()),
    path('users/me/', views.UserMeView.as_view()),
    path('users/me/avatar/', views.AvatarView.as_view()),
    path('users/<int:pk>/', views.UserDetailView.as_view()),
    path('auth/', include('djoser.urls.authtoken')),
]

urlpatterns += router.urls
