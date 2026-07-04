from django.contrib import admin
from .models import Persons, CustomUser, TimeManagementLog, TaskStatus, Games, PersonGame, TaskType
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ImportExportModelAdmin
from .resources import PersonResource, GameResource, PersonGameResource
# Register your models here.

@admin.register(Persons)
class PersonAdmin(ImportExportModelAdmin):
    resource_class = PersonResource
    list_display = ('name', 'phone_number')

@admin.register(Games)
class GameAdmin(ImportExportModelAdmin):
    resource_class = GameResource
    display = 'name'

@admin.register(PersonGame)
class PersonGameAdmin(ImportExportModelAdmin):
    resource_class = PersonGameResource
    list_display = ('person', 'game', 'played_at')


@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'status')


@admin.register(TaskType)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('role',),
        }),
    )
    list_display = ['username', 'role', 'first_name', 'last_name']
    list_filter = ['role']


@admin.register(TimeManagementLog)
class TimeManagementLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'created_at', 'time_management']
    list_filter = ['created_at', 'user']