from ninja import Schema
from typing import Optional
from datetime import date
from enum import Enum
from pydantic import BaseModel, root_validator
from datetime import datetime
from django.utils.formats import date_format
from django.utils.timezone import localtime


class AddContactRequest(Schema):
    first_name: str
    phone_number: str
    comment_field: Optional[str]


class AddTaskRequest(Schema):
    title: str
    description: Optional[str]
    user: int
    person: int
    is_important: Optional[bool] = False
    is_invite: Optional[bool] = False
    task_type: int


class TimeManagementUpdateSchema(BaseModel):
    time_management: Optional[date] = None
    clear: Optional[bool] = False


class TaskResponseSchema(BaseModel):
    id: int
    time_management: Optional[date] = None
    section: str
    title: str
    created_at: datetime
    comment: Optional[str]
    is_important: Optional[bool] = False
    get_absolute_url: str
    formatted_created_at: str = None

    @root_validator(pre=True)
    def format_datetime(cls, values):
        created_at = values.get("created_at")
        if created_at:
            created_at_local = localtime(created_at)
            values["formatted_created_at"] = date_format(created_at_local, "d E Y г. H:i", use_l10n=True)
        return values


class StatusEnum(str, Enum):
    GOOD = "good"
    BAD = "bad"
    NO_CONTACT = "no-contact"


class TaskPersonUpdateSchema(Schema):
    name: str
    surname: str
    patronymic: str
    phone_number: str
    birthdate: Optional[date]
    chat_status: Optional[bool]
    comment: Optional[str]

