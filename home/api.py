from ninja import Router
from .schema import AddContactRequest, AddTaskRequest
from django.shortcuts import get_object_or_404
from django.utils.timezone import localdate
from datetime import timedelta
from .models import Persons, TaskStatus, Tasks, UserTask, TimeManagementLog, CommentLog, TaskType
from django.views.decorators.csrf import csrf_protect
from .schema import TimeManagementUpdateSchema, TaskResponseSchema, StatusEnum
from django.http import JsonResponse
from django.shortcuts import redirect
from .forms import PersonForm, TaskForm
import re
from datetime import datetime

router = Router()


@router.post("/add-contact/")
@csrf_protect
def add_contact(request, data: AddContactRequest):
    person = Persons.objects.create(
        first_name=data.first_name,
        phone_number=data.phone_number,
        comment_field=data.comment_field
    )
    return {
        "success": True,
        "person": {
            "id": person.id,
            "first_name": person.first_name,
            "phone_number": person.phone_number,
            "comment_field": person.comment_field,
            "get_absolute_url": person.get_absolute_url(),
            "time_management": person.time_management,
        }
    }


@router.post("task/create/")
@csrf_protect
def add_task(request, data: AddTaskRequest):
    person = get_object_or_404(Persons, id=data.person)

    # Контакт недоступен для новых задач
    person.is_active = True
    person.save()

    task_type = TaskType.objects.get(id=data.task_type)

    task = Tasks.objects.create(
        title=data.title,
        description=data.description,
        user_id=data.user,
        person_id=data.person,
        is_important=data.is_important,
        is_invite=data.is_invite,
        task_type=task_type,
    )
    UserTask.objects.create(user_id=data.user, task=task)
    return {
        "success": True, "task_id": task.id
    }


@router.delete("task/{task_id}/delete/")
def delete_task(request, task_id: int):
    task = get_object_or_404(Tasks, id=task_id)
    task.delete()

    # Контакт доступен для новой задачи
    task.person.is_active = False
    task.person.save()
    return {"success": True}


@router.post("task/{task_id}/update-time-management/", response=TaskResponseSchema)
@csrf_protect
def update_time_management(request, task_id: int, payload: TimeManagementUpdateSchema):
    task = get_object_or_404(Tasks, id=task_id)
    today = localdate()
    tomorrow = today + timedelta(days=1)

    if payload.clear:
        task.time_management = None
        section = "main"
    elif payload.time_management:
        task.time_management = payload.time_management

        # Определение секции
        if payload.time_management < today:
            section = "expired"
        elif payload.time_management == today:
            section = "today"
        elif payload.time_management == tomorrow:
            section = "tomorrow"
        else:
            section = "later"
    else:
        return JsonResponse({"status": "error", "message": "Invalid input"}, status=400)

    task.save()

    TimeManagementLog.objects.create(
        task=task,
        user=request.user,
        time_management=payload.time_management,
    )

    return {
        "id": task.id,
        "time_management": task.time_management,
        "section": section,
        "title": task.title,
        "created_at": task.created_at,
        "comment": task.comment,
        "is_important": task.is_important,
        "get_absolute_url": task.get_absolute_url(),
    }


@router.post("task/{task_id}/{status}/")
@csrf_protect
def update_status(request, task_id: int, status: StatusEnum):
    task = Tasks.objects.get(id=task_id)

    if status == "good":
        new_status = True
    elif status == "no-contact":
        new_status = True
        task.person.is_contact = False
    else:
        new_status = False

    task.time_management = None
    task.status = new_status
    task.completed_at = datetime.now()
    task.save()
    # Логируем результат выполнения задачи
    TaskStatus.objects.create(
        task=task,
        user=request.user,
        status=new_status,
    )
    # Контакт доступен для новой задачи
    task.person.is_active = False
    task.person.save()
    return redirect('task-list')


@router.post("task/{task_id}/reup/")
@csrf_protect
def reup_task(request, task_id: int):
    task = get_object_or_404(Tasks, id=task_id)
    form = TaskForm(request.POST, instance=task)

    if form.is_valid():
        task = form.save(commit=False)
        task.status = None
        task.completed_at = None
        task.save()
        # Проверка не изменился ли ответственный
        if task.user != form.initial['user']:
            # Не создавать дубликатов, если этот же ответственный был назначен до нового
            if not UserTask.objects.filter(task=task, user=task.user).exists():
                UserTask.objects.create(user=task.user, task=task)
        # Контакт снова занят задачей
        task.person.is_active = True
        task.person.save()

    return redirect('manager-task-list')


@router.post("task/{task_id}/edit/")
@csrf_protect
def edit_task(request, task_id: int):
    task = get_object_or_404(Tasks, id=task_id)
    form = TaskForm(request.POST, instance=task)

    if form.is_valid():
        task = form.save()
        task.save()
        # Проверка не изменился ли ответственный
        if task.user != form.initial['user']:
            # Не создавать дубликатов, если этот же ответственный был назначен до нового
            if not UserTask.objects.filter(task=task, user=task.user).exists():
                UserTask.objects.create(user=task.user, task=task)

    return redirect('manager-task-list')


@router.post("/task-person/save/")
@csrf_protect
def update_person(request, task_id: int, person_id: int):
    person = get_object_or_404(Persons, id=person_id)
    task = get_object_or_404(Tasks, id=task_id)
    form = PersonForm(request.POST, instance=person)
    new_comment = request.POST.get("comment")
    birthdate = request.POST.get("birthdate")

    if birthdate:
        try:
            person.birthdate = birthdate
        except ValueError:
            return JsonResponse({"success": False, "errors": {"birthdate": "Invalid date format"}}, status=400)

    if form.is_valid():
        # Перед сохранением удаляем все знаки кроме чисел и '+'
        cleaned_phone_number = re.sub(r'[^0-9+]', '', person.phone_number)
        person.phone_number = cleaned_phone_number

        form.save()
        person.save()
        # Создаем лог нового комментария
        if new_comment and new_comment != task.comment:
            CommentLog.objects.create(
                task=task,
                user=request.user,
                comment=new_comment,
            )
            task.comment = new_comment
        task.save()

        messageapp_link = f"https://somemessageapp.message/{person.phone_number}?text=Здравствуйте! Это Клуб Инновация VR. Хотите быть в курсе всех наших новых акций и спецпредложений? Присоединяйтесь к нашему чату, где вы будете первыми узнавать о лучших предложениях и новых играх! Переходите по ссылке, чтобы вступить в чат: [ссылка на чат]. Будем рады видеть вас снова в нашем клубе! Ваш Инновация VR"
        return JsonResponse({"success": True,
                             "message": "Fields updated successfully.",
                             "messageapp_link": messageapp_link})
    else:
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

