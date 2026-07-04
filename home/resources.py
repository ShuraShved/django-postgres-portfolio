from import_export import resources
from .models import Persons, Games, PersonGame


class PersonResource(resources.ModelResource):
    class Meta:
        model = Persons


class GameResource(resources.ModelResource):
    class Meta:
        model = Games


class PersonGameResource(resources.ModelResource):
    class Meta:
        model = PersonGame
