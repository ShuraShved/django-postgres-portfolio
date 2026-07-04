from django.urls import path
from . import views
from .views import CustomLoginView
from django.contrib.auth.views import LogoutView
from .api import edit_task

urlpatterns = [
    path('', views.HomeRedirectView.as_view(), name='home'),

    # URLs Входа
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # URLs Сотрудника
    path("tasks/", views.TaskListView.as_view(), name="task-list"),
    path("tasks/<int:pk>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("task/<int:pk>/view", views.TaskView.as_view(), name="task-view"),

    # URLs Руководителя
    path("manager/statistics/", views.ManagerStatisticsView.as_view(), name="manager-statistics"),
    path("manager/tasks/", views.ManagerTaskListView.as_view(), name="manager-task-list"),
    path("manager/contacts/", views.ManagerContactListView.as_view(), name="manager-contact-list"),
    path("manager/contacts/<int:pk>", views.ManagerPersonDetailView.as_view(), name="manager-person-detail"),
    path("manager/tasks/new/<int:person_id>", views.ManagerTaskCreateView.as_view(), name="manager-task-create"),
    path("manager/tasks/<int:pk>/edit/", views.ManagerTaskEditView.as_view(), name="manager-task-edit"),
    path("manager/tasks/<int:pk>/view/", views.ManagerTaskView.as_view(), name="manager-task-view"),

    # API
    path("task/<int:task_id>/edit/", edit_task, name="edit-task")
]