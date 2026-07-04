from django import forms
from django.utils import timezone

from .models import Persons, Tasks, TaskType
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Q


class LoginForm(AuthenticationForm):
    """
    Форма входа в систему.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Имя пользователя'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Пароль'})
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


class PersonForm(forms.ModelForm):
    class Meta:
        model = Persons
        fields = ['name', 'surname', 'patronymic', 'phone_number', 'chat_status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'patronymic': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.DateInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Оставляем данные, если поля не были заполнены
        for field in self.fields:
            if not cleaned_data.get(field):
                cleaned_data[field] = getattr(self.instance, field)


class TaskForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.filter(is_staff=False),
        label="Назначить:",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="Выбрать сотрудника"
    )
    task_type = forms.ModelChoiceField(
        queryset=TaskType.objects.all(),
        label="Классификация:",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="Выбрать класс задачи"
    )

    # Отображение имени и фамилии сотрудника (вместо username)
    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)

        self.fields['user'].queryset = (
            get_user_model()
            .objects.filter(is_staff=False)
            .annotate(active_task_count=Count('tasks', filter=Q(tasks__status=None)))
        )

        self.fields['user'].label_from_instance = lambda user: (
            f"{user.first_name} {user.last_name} (Активных задач: {user.active_task_count})"
        )

    class Meta:
        model = Tasks
        fields = ['title', 'description', 'user', 'is_important', 'is_invite', 'task_type']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'time_management': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_time_management(self):
        time_management = self.cleaned_data.get('time_management')
        if time_management and time_management < timezone.now().date():
            raise forms.ValidationError("Дата не может быть в прошлом.")
        return time_management
