from django.db import models
from django.urls import reverse
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
# Create your models here.


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('manager', 'Руководитель'),
        ('staff', 'Сотрудник'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return self.username


class PhoneNumberField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 20  # Максимальная длина для телефонных номеров с форматированием
        kwargs['validators'] = [
            RegexValidator(
                r'^(\s*)?(\+)?([- _():=+]?\d[- _():=+]?){10,14}(\s*)?$',
                'Введите номер телефона в правильном формате'
            )
        ]
        super().__init__(*args, **kwargs)


class Persons(models.Model):
    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255, blank=True, null=True)
    patronymic = models.CharField(max_length=255, blank=True, null=True)
    phone_number = PhoneNumberField(default="00000000000", blank=False)
    birthdate = models.DateField(blank=True, null=True)
    chat_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    is_contact = models.BooleanField(default=True)
    last_task_date = models.DateField(null=True, blank=True)

    def __str__(self):
        """
        String for representing the Model object.
        """
        return '%s, %s' % (self.name, self.phone_number)

    def get_last_played_game(self):
        last_person_game = self.person_game.order_by('-played_at').first()  # Дата последней игры
        return last_person_game.played_at if last_person_game else "Не играл"

    def get_game_count(self):
        return self.person_game.count()


class Games(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class PersonGame(models.Model):
    person = models.ForeignKey(Persons, on_delete=models.CASCADE, related_name="person_game")
    game = models.ForeignKey(Games, on_delete=models.CASCADE, related_name="person_game")
    played_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.person.name} played {self.game.name}"

    class Meta:
        db_table = "home_person_game"


class TaskType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "task_type"


class Tasks(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Заголовок"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Описание"))
    time_management = models.DateField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True, verbose_name=_("Комментарий"))
    status = models.BooleanField(null=True, blank=True)
    is_important = models.BooleanField(default=False, verbose_name=_("Важная задача"))
    is_invite = models.BooleanField(default=False, verbose_name=_("Пригласить в промо-чат"))
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateField(null=True, blank=True)
    person = models.ForeignKey(Persons, on_delete=models.CASCADE, related_name="tasks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="tasks", null=True)
    task_type = models.ForeignKey(TaskType, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks",
                                  verbose_name=_("Класс задачи"))

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("manager-task-edit", kwargs={"pk": self.pk})


@receiver(post_save, sender=Tasks)
def update_last_task_date(sender, instance, **kwargs):
    if instance.status and instance.completed_at:
        person = instance.person
        person.last_task_date = instance.completed_at
        person.save()


class UserTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="user_tasks", null=True)
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE, related_name="user_tasks")

    def __str__(self):
        return f"User: {self.user.username}, Task: {self.task.title}"

    class Meta:
        db_table = "home_user_task"


class TimeManagementLog(models.Model):
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE, related_name='time_logs', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='time_logs', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    time_management = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Log for {self.task} by {self.user} at {self.created_at}"

    class Meta:
        db_table = "home_time_management_log"


class CommentLog(models.Model):
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE, related_name='comment_logs', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='comment_logs', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Log for {self.task} by {self.user} at {self.created_at}"

    class Meta:
        db_table = "home_comment_log"


class TaskStatus(models.Model):
    task = models.ForeignKey(Tasks, on_delete=models.CASCADE, related_name='status_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='status_logs', null=True)
    status = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for {self.task} by {self.user} at {self.created_at}"

    class Meta:
        db_table = "home_task_status"
