from django.views import generic
from .forms import PersonForm, TaskForm
from django.shortcuts import get_object_or_404
from .models import Persons, Tasks, PersonGame
from django.utils.timezone import now, timedelta
from datetime import datetime
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import RedirectView
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from babel.dates import format_date
from django.db.models import OuterRef, Subquery
from django.db.models import F
from django.db.models.functions import ExtractMonth, ExtractDay
from datetime import date
from django.db.models import Case, When, Value, IntegerField


class CustomLoginView(LoginView):
    """
    Представление для входа в систему.
    """
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        # Переадресация по роли
        if self.request.user.is_superuser or self.request.user.is_staff:
            return reverse_lazy('manager-contact-list')
        return reverse_lazy('task-list')


class HomeRedirectView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_superuser or self.request.user.is_staff:
            return reverse_lazy('manager-contact-list')
        return reverse_lazy('task-list')


def format_birthdate_no_year(date):
    return format_date(date, format='d MMMM', locale='ru')


# Сортировка
class SortingMixin:
    default_sort_field = "id"
    default_sort_direction = "asc"
    sortable_fields = []

    def get_sort_field(self):
        sort_field = self.request.GET.get("sort", self.default_sort_field)
        direction = self.request.GET.get("direction", self.default_sort_direction)

        if sort_field.lstrip("-") not in self.sortable_fields:
            sort_field = self.default_sort_field

        return f"-{sort_field}" if direction == "desc" else sort_field

    def get_queryset(self):
        queryset = super().get_queryset()
        sort_field = self.get_sort_field()

        if sort_field == "birthdate":
            today = date.today()
            current_month = today.month
            current_day = today.day

            queryset = queryset.annotate(
                birth_month=ExtractMonth('birthdate'),
                birth_day=ExtractDay('birthdate')
            )

            queryset = queryset.annotate(
                next_birthday_month_diff=(F('birth_month') - current_month) % 12,
                next_birthday_day_diff=(F('birth_day') - current_day) % 31
            )

            queryset = queryset.annotate(
                next_birthday_diff=(F('next_birthday_month_diff') * 31 + F('next_birthday_day_diff'))
            )

        if 'game_count' in sort_field:
            queryset = queryset.annotate(game_count=Count("person_game__id"))

        if 'last_played_at' in sort_field:
            last_played_game = PersonGame.objects.filter(person_id=OuterRef("id")).order_by("-played_at")
            queryset = queryset.annotate(last_played_at=Subquery(last_played_game.values("played_at")[:1]))

        return queryset.order_by(sort_field)


# Сортировка клиентов
class PersonsSortingMixin:
    default_sort_field = "id"
    default_sort_direction = "asc"
    sortable_fields = []

    def get_sort_field(self):
        sort_field = self.request.GET.get("sort", self.default_sort_field)
        direction = self.request.GET.get("direction", self.default_sort_direction)

        if sort_field.lstrip("-") not in self.sortable_fields:
            sort_field = self.default_sort_field

        return f"-{sort_field}" if direction == "desc" else sort_field

    def get_queryset(self):
        queryset = super().get_queryset()
        sort_field = self.get_sort_field()

        # Separate contacts and non-contacts
        contact_queryset = queryset.filter(is_contact=True)
        non_contact_queryset = queryset.filter(is_contact=False)

        # Apply sorting to contact queryset
        if sort_field == "birthdate":
            today = date.today()
            current_month = today.month
            current_day = today.day

            contact_queryset = contact_queryset.annotate(
                birth_month=ExtractMonth('birthdate'),
                birth_day=ExtractDay('birthdate')
            )

            contact_queryset = contact_queryset.annotate(
                next_birthday_month_diff=(F('birth_month') - current_month) % 12,
                next_birthday_day_diff=(F('birth_day') - current_day) % 31
            )

            contact_queryset = contact_queryset.annotate(
                next_birthday_diff=(F('next_birthday_month_diff') * 31 + F('next_birthday_day_diff'))
            )

        if 'game_count' in sort_field:
            contact_queryset = contact_queryset.annotate(game_count=Count("person_game__id"))

        if 'last_played_at' in sort_field:
            last_played_game = PersonGame.objects.filter(person_id=OuterRef("id")).order_by("-played_at")
            contact_queryset = contact_queryset.annotate(last_played_at=Subquery(last_played_game.values("played_at")[:1]))

        # Combine and sort the contact and non-contact querysets, prioritizing contacts
        queryset = contact_queryset | non_contact_queryset

        # Add a condition to sort non-contact persons to the end of the list
        queryset = queryset.annotate(
            is_contact_priority=Case(
                When(is_contact=False, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        )

        return queryset.order_by('is_contact_priority', sort_field)


class ManagerOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff


class BreadcrumbMixin:
    def get_breadcrumbs(self):
        # Получаем хлебные крошки из сессии
        return self.request.session.get('breadcrumbs', [])

    def add_breadcrumb(self, name, url):
        breadcrumbs = self.get_breadcrumbs()

        # Проверка если крошка уже существует
        if breadcrumbs and any(bc['url'] == url for bc in breadcrumbs):
            index = next(i for i, bc in enumerate(breadcrumbs) if bc['url'] == url)
            breadcrumbs = breadcrumbs[:index + 1]
        else:
            breadcrumbs.append({'name': name, 'url': url})

        self.request.session['breadcrumbs'] = breadcrumbs

    # Функция очистки всех хлебных крошек
    def clear_breadcrumbs(self):
        self.request.session['breadcrumbs'] = []

    # Функция удаления последней хлебной крошки
    def remove_last_breadcrumb(self):
        breadcrumbs = self.get_breadcrumbs()
        if breadcrumbs:
            breadcrumbs.pop()
        self.request.session['breadcrumbs'] = breadcrumbs


class TaskListView(LoginRequiredMixin, SortingMixin, generic.ListView):
    """
    Отображение всех задач (сотрудник)
    """
    model = Tasks
    template_name = "tasks/task_list.html"
    sortable_fields = ["is_important", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user
        if user.is_staff or user.is_superuser:
            queryset = queryset.exclude(completed_at__isnull=False)
        else:
            queryset = queryset.filter(user=user).exclude(completed_at__isnull=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = datetime.today().date()
        tomorrow = today + timedelta(days=1)

        tasks = self.get_queryset()

        if user.is_staff or user.is_superuser:
            context["today"] = tasks.filter(time_management=today).exclude(completed_at__isnull=False)
            context["tomorrow"] = tasks.filter(time_management=tomorrow).exclude(completed_at__isnull=False)
            context["later"] = tasks.filter(time_management__gt=tomorrow).exclude(completed_at__isnull=False)
            context["expired"] = tasks.filter(time_management__lt=today).exclude(completed_at__isnull=False)
            context["main"] = tasks.filter(time_management=None).exclude(completed_at__isnull=False)
        else:
            context["today"] = tasks.filter(
                user=self.request.user,
                time_management=today).exclude(completed_at__isnull=False)
            context["tomorrow"] = tasks.filter(
                user=self.request.user,
                time_management=tomorrow).exclude(completed_at__isnull=False)
            context["later"] = tasks.filter(
                user=self.request.user,
                time_management__gt=tomorrow).exclude(completed_at__isnull=False)
            context["expired"] = tasks.filter(
                user=self.request.user,
                time_management__lt=today).exclude(completed_at__isnull=False)
            context["main"] = tasks.filter(time_management=None).exclude(completed_at__isnull=False)

        context["sort"] = self.request.GET.get("sort", self.default_sort_field)
        context["direction"] = self.request.GET.get("direction", self.default_sort_direction)

        return context


class TaskDetailView(LoginRequiredMixin, generic.UpdateView):
    """
    Отображение подробностей задачи (сотрудник)
    """
    model = Tasks
    template_name = "tasks/task_detail.html"
    fields = ["comment"]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['comment'].widget.attrs.update({'class': 'form-control'})
        return form

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            "time_logs__user",
            "person__person_game__game"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()
        person = task.person

        # Сообщение в какое-нибудь приложение
        messageapp_link = f"https://somemessageapp.message/{person.phone_number}?text=Здравствуйте! Это Клуб Инновация VR. Хотите быть в курсе всех наших новых акций и спецпредложений? Присоединяйтесь к нашему чату, где вы будете первыми узнавать о лучших предложениях и новых играх! Переходите по ссылке, чтобы вступить в чат: [ссылка на чат]. Будем рады видеть вас снова в нашем клубе! Ваш Инновация VR"
        context["messageapp_link"] = messageapp_link

        # Ранее завершенные задачи
        tasks = person.tasks.filter(status__isnull=False)

        # Возраст
        if person and person.birthdate:
            today = date.today()
            age = (
                    today.year - person.birthdate.year
                    - ((today.month, today.day) < (person.birthdate.month, person.birthdate.day))
            )
            context["person_age"] = age
        # Игры
        person_games = person.person_game.select_related("game").all().order_by('-played_at')
        context["person_games"] = person_games

        context["task"] = task
        context["tasks"] = tasks
        context["person_form"] = PersonForm(instance=task.person)
        context["show_breadcrumb"] = True
        return context


class ManagerPersonDetailView(LoginRequiredMixin, ManagerOnlyMixin, BreadcrumbMixin, generic.DetailView):
    """
    Отображение подробностей контакта
    """
    model = Persons
    template_name = "tasks/manager_contact_detail.html"
    sortable_fields = ["id", "status", "created_at", "completed_at"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.get_object()

        # Так как SortingMixin зависит от модели во view, задачи сортируются отдельной логикой здесь
        sort_field = self.request.GET.get("sort", "id")
        direction = self.request.GET.get("direction", "asc")
        if sort_field not in self.sortable_fields:
            sort_field = "id"
        sort_field = f"-{sort_field}" if direction == "desc" else sort_field

        tasks = Tasks.objects.filter(person=person).order_by(sort_field)

        # Возраст
        if person and person.birthdate:
            today = date.today()
            age = (
                    today.year - person.birthdate.year
                    - ((today.month, today.day) < (person.birthdate.month, person.birthdate.day))
            )
            context["person_age"] = age

        # Игры
        person_games = person.person_game.select_related("game").all().order_by('-played_at')
        context["person_games"] = person_games

        person.latest_task = person.tasks.order_by('-created_at').first()

        context['person'] = person
        context['tasks'] = tasks
        context["show_breadcrumb"] = True
        context["sort"] = sort_field.lstrip('-')
        context["direction"] = direction
        #self.clear_breadcrumbs()
        #self.add_breadcrumb("Список контактов", reverse('manager-contact-list'))
        self.add_breadcrumb("Клиент", self.request.path)
        context["breadcrumbs"] = self.get_breadcrumbs()

        return context


class ManagerTaskListView(LoginRequiredMixin, ManagerOnlyMixin, BreadcrumbMixin, SortingMixin, generic.ListView):
    """
    Отображение всех задач
    """
    model = Tasks
    template_name = "tasks/manager_task_list.html"
    paginate_by = 15

    sortable_fields = ["id", "status", "created_at", "completed_at"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sort"] = self.request.GET.get("sort", self.default_sort_field)
        context["direction"] = self.request.GET.get("direction", self.default_sort_direction)

        self.clear_breadcrumbs()
        self.add_breadcrumb("Список задач", self.request.path)
        context["breadcrumbs"] = self.get_breadcrumbs()
        return context


class ManagerTaskCreateView(LoginRequiredMixin, ManagerOnlyMixin, BreadcrumbMixin, generic.CreateView):
    """
    Отображение страницы создания задачи
    """
    model = Tasks
    form_class = TaskForm
    template_name = "tasks/manager_task_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person_id = self.kwargs.get('person_id')
        person = get_object_or_404(Persons, id=person_id)
        context['person'] = person
        context["show_breadcrumb"] = True
        self.add_breadcrumb("Создание задачи", self.request.path)
        context["breadcrumbs"] = self.get_breadcrumbs()
        return context

    def form_valid(self, form):
        person_id = self.kwargs['person_id']
        form.instance.person_id = person_id
        person = get_object_or_404(Persons, id=person_id)
        # блокирует создание новых задач
        person.is_active = True
        person.save()
        return super().form_valid(form)


class ManagerContactListView(LoginRequiredMixin, ManagerOnlyMixin, BreadcrumbMixin, PersonsSortingMixin, generic.ListView):
    """
    Отображение всех контактов
    """
    model = Persons
    template_name = "tasks/manager_contact_list.html"
    paginate_by = 15

    sortable_fields = ["id", "birthdate", "last_played_at", "game_count", "chat_status", "last_task_date"]

    def get_queryset(self):
        queryset = super().get_queryset()

        sort_field = self.request.GET.get("sort", "id")
        direction = self.request.GET.get("direction", "asc")

        # Сортировка по полю 'birthdate'
        if sort_field == "birthdate":
            today = date.today()
            current_month = today.month
            current_day = today.day

            queryset = queryset.annotate(
                birth_month=ExtractMonth('birthdate'),
                birth_day=ExtractDay('birthdate')
            )

            queryset = queryset.annotate(
                next_birthday_month_diff=(F('birth_month') - current_month) % 12,
                next_birthday_day_diff=(F('birth_day') - current_day) % 31
            )

            queryset = queryset.annotate(
                next_birthday_diff=(F('next_birthday_month_diff') * 31 + F('next_birthday_day_diff'))
            )

            if direction == "desc":
                queryset = queryset.order_by('-next_birthday_diff')
            else:
                queryset = queryset.order_by('next_birthday_diff')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        paginated_persons = context['object_list']
        for person in paginated_persons:

            # Последнее время игры
            last_played_game = PersonGame.objects.filter(person_id=person.id).order_by('-played_at').first()
            person.last_played_at = last_played_game.played_at if last_played_game else "Не играл"

            # Количество сыгранных игр
            person.game_count = person.person_game.count()

            # Последняя задача для каждого контакта
            person.latest_task = person.tasks.order_by('-created_at').first()

            # Грамматически корректное отображения даты рождения (без года)
            person.birthdate_formatted = format_birthdate_no_year(person.birthdate)

        context['persons'] = paginated_persons

        context["sort"] = self.request.GET.get("sort", self.default_sort_field)
        context["direction"] = self.request.GET.get("direction", self.default_sort_direction)

        self.clear_breadcrumbs()
        self.add_breadcrumb("Список клиентов", self.request.path)
        context["breadcrumbs"] = self.get_breadcrumbs()

        return context


class ManagerTaskEditView(LoginRequiredMixin, ManagerOnlyMixin, BreadcrumbMixin, generic.UpdateView):
    """
    Отображение страницы редактирования задач
    """
    model = Tasks
    template_name = "tasks/manager_task_edit.html"
    form_class = TaskForm

    def form_valid(self, form):

        response = super().form_valid(form)
        # Возвращает после сохранения назад
        next_url = self.request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_breadcrumb"] = True
        self.add_breadcrumb("Редактирование задачи", self.request.path)
        context["breadcrumbs"] = self.get_breadcrumbs()

        # Логи
        task = self.get_object()
        logs = list(task.time_logs.all()) + list(task.status_logs.all()) + list(task.comment_logs.all())
        for log in logs:
            if hasattr(log, 'time_management'):
                log.log_type = "time"
            elif hasattr(log, 'comment'):
                log.log_type = "comment"
            elif hasattr(log, 'status'):
                log.log_type = "status"
        logs.sort(key=lambda log: log.created_at, reverse=True)
        context["logs"] = logs

        person = task.person
        context["person"] = person
        context["task"] = task
        return context


class ManagerTaskView(LoginRequiredMixin, ManagerOnlyMixin, BreadcrumbMixin, generic.DetailView):
    """
    Отображение страницы просмотра задачи
    """
    model = Tasks
    template_name = "tasks/manager_task_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_breadcrumb"] = True
        self.add_breadcrumb("Просмотр задачи", self.request.path)
        context["breadcrumbs"] = self.get_breadcrumbs()

        # Логи
        task = self.get_object()
        logs = list(task.time_logs.all()) + list(task.status_logs.all()) + list(task.comment_logs.all())
        for log in logs:
            if hasattr(log, 'time_management'):
                log.log_type = "time"
            elif hasattr(log, 'comment'):
                log.log_type = "comment"
            elif hasattr(log, 'status'):
                log.log_type = "status"
        logs.sort(key=lambda log: log.created_at, reverse=True)
        context["logs"] = logs

        person = task.person
        context["person"] = person
        context["task"] = task
        return context


class TaskView(LoginRequiredMixin, BreadcrumbMixin, generic.DetailView):
    """
    Отображение страницы просмотра задачи (для сотрудника)
    """
    model = Tasks
    template_name = "tasks/task_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_breadcrumb"] = True
        self.add_breadcrumb("Просмотр задачи", self.request.path)
        context["breadcrumbs"] = self.get_breadcrumbs()

        # Логи
        task = self.get_object()
        logs = list(task.time_logs.all()) + list(task.status_logs.all()) + list(task.comment_logs.all())
        for log in logs:
            if hasattr(log, 'time_management'):
                log.log_type = "time"
            elif hasattr(log, 'comment'):
                log.log_type = "comment"
            elif hasattr(log, 'status'):
                log.log_type = "status"
        logs.sort(key=lambda log: log.created_at, reverse=True)
        context["logs"] = logs

        person = task.person
        context["person"] = person
        context["task"] = task
        return context


class ManagerStatisticsView(LoginRequiredMixin, ManagerOnlyMixin, generic.View):
    """
    Отображение страницы со статистикой
    """
    template_name = "tasks/manager_statistics.html"

    def get(self, request, *args, **kwargs):
        months = [
            (1, "Январь"), (2, "Февраль"), (3, "Март"), (4, "Апрель"),
            (5, "Май"), (6, "Июнь"), (7, "Июль"), (8, "Август"),
            (9, "Сентябрь"), (10, "Октябрь"), (11, "Ноябрь"), (12, "Декабрь"),
        ]
        selected_month = int(request.GET.get('month', now().month))
        selected_year = int(request.GET.get('year', now().year))
        selected_month_name = dict(months).get(selected_month, "Неизвестный месяц")

        # Общая статистика
        total_persons = Persons.objects.count()
        total_tasks = Tasks.objects.filter(created_at__year=selected_year, created_at__month=selected_month).count()
        completed_tasks = Tasks.objects.filter(
            completed_at__year=selected_year, completed_at__month=selected_month, status__isnull=False
        ).count()
        pending_tasks = Tasks.objects.filter(
            created_at__year=selected_year, created_at__month=selected_month, status=None
        ).count()
        loyalty_tasks = Tasks.objects.filter(
            created_at__year=selected_year, created_at__month=selected_month, task_type__name="Повышение лояльности"
        ).count()
        presale_tasks = Tasks.objects.filter(
            created_at__year=selected_year, created_at__month=selected_month, task_type__name="Предпродажные коммуникации"
        ).count()

        # Статистика по сотрудникам
        User = get_user_model()
        users = User.objects.filter(is_staff=False).annotate(
            total_tasks=Count(
                'tasks',
                filter=Q(tasks__created_at__year=selected_year, tasks__created_at__month=selected_month)
            ),
            loyalty_tasks=Count(
                'tasks',
                filter=Q(tasks__created_at__year=selected_year, tasks__created_at__month=selected_month,
                         tasks__task_type__name="Повышение лояльности")
            ),
            presale_tasks=Count(
                'tasks',
                filter=Q(tasks__created_at__year=selected_year, tasks__created_at__month=selected_month,
                         tasks__task_type__name="Предпродажные коммуникации")
            ),
            good_tasks=Count(
                'tasks',
                filter=Q(tasks__status=True, tasks__created_at__year=selected_year,
                         tasks__created_at__month=selected_month)
            ),
            bad_tasks=Count(
                'tasks',
                filter=Q(tasks__status=False, tasks__created_at__year=selected_year,
                         tasks__created_at__month=selected_month)
            ),
            pending_tasks=Count(
                'tasks',
                filter=Q(tasks__status__isnull=True, tasks__created_at__year=selected_year,
                         tasks__created_at__month=selected_month)
            ),
            completed_tasks=Count(
                'tasks',
                filter=Q(tasks__completed_at__year=selected_year, tasks__completed_at__month=selected_month)
            ),
        )

        context = {
            'selected_month': selected_month,
            'selected_year': selected_year,
            'selected_month_name': selected_month_name,
            'total_persons': total_persons,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'loyalty_tasks': loyalty_tasks,
            'presale_tasks': presale_tasks,
            'user_statistics': users,
            'months': months,
            'years': range(2024, now().year + 1),
        }

        return render(request, self.template_name, context)
