from django.shortcuts import redirect

from recipes.models import Recipe


def redirect_to_recipe(request, code):
    try:
        recipe = Recipe.objects.get(short_code=code)
    except Recipe.DoesNotExist:
        return redirect('/?error=not_found')
    return redirect(f'/recipes/{recipe.id}/')
