from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
    model_validator,
)

Name = Annotated[str, Field(min_length=1, max_length=160)]
Text = Annotated[str, Field(min_length=1, max_length=10000)]
Positive = Annotated[int, Field(gt=0, strict=True)]
Money = Annotated[int, Field(ge=0, le=100000000, strict=True)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_serializer("*", mode="wrap")
    def canonical_dates(self, value, handler):
        if isinstance(value, datetime):
            return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return handler(value)

    @field_validator("*", mode="after")
    @classmethod
    def utc_dates(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("Une date ISO 8601 avec fuseau horaire est requise")
            return value.astimezone(UTC)
        return value


class UserCreate(Model):
    email: EmailStr
    first_name: Name
    last_name: Name
    password: Annotated[str, Field(min_length=10, max_length=128)]
    bio: Annotated[str, Field(max_length=2000)] = ""
    avatar_url: HttpUrl | None = None


class UserUpdate(Model):
    email: EmailStr
    first_name: Name
    last_name: Name
    bio: Annotated[str, Field(max_length=2000)] = ""
    avatar_url: HttpUrl | None = None


class PasswordChange(Model):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class Login(Model):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GroupInput(Model):
    name: Name
    description: Text
    icon: Name
    cover_url: HttpUrl
    visibility: Literal["public", "private", "secret"]
    members_can_post: bool = True
    members_can_create_events: bool = True


class GroupCreate(GroupInput):
    member_ids: list[Positive] = Field(default_factory=list, max_length=1000)
    admin_ids: list[Positive] = Field(default_factory=list, max_length=100)


class GroupRole(Model):
    role: Literal["admin", "member"] = "member"


class EventRole(Model):
    role: Literal["organizer", "participant"] = "participant"


class EventInput(Model):
    name: Name
    description: Text
    starts_at: datetime
    ends_at: datetime
    location: Name
    cover_url: HttpUrl
    visibility: Literal["public", "private"]

    @model_validator(mode="after")
    def ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("La fin doit être postérieure au début")
        return self


class EventCreate(EventInput):
    group_id: Positive | None = None
    organizer_ids: list[Positive] = Field(default_factory=list, max_length=100)
    participant_ids: list[Positive] = Field(default_factory=list, max_length=1000)
    invite_all_group_members: bool = False


class EventSettings(Model):
    shopping_enabled: bool = False
    carpool_enabled: bool = False
    ticketing_enabled: bool = False


class ThreadInput(Model):
    title: Name
    group_id: Positive | None = None
    event_id: Positive | None = None

    @model_validator(mode="after")
    def exclusive_parent(self):
        if (self.group_id is None) == (self.event_id is None):
            raise ValueError("Le fil doit appartenir à un groupe OU à un événement")
        return self


class ThreadUpdate(Model):
    title: Name


class Content(Model):
    content: Text


class AlbumInput(Model):
    name: Name
    description: str = Field(default="", max_length=10000)


class PhotoInput(Model):
    url: HttpUrl
    caption: str = Field(default="", max_length=2000)


class Question(Model):
    text: Name
    options: list[Name] = Field(min_length=2, max_length=20)

    @model_validator(mode="after")
    def unique_options(self):
        if len({s.casefold() for s in self.options}) != len(self.options):
            raise ValueError("Les options d'une question doivent être distinctes")
        return self


class PollInput(Model):
    title: Name
    questions: list[Question] = Field(min_length=1, max_length=50)


class PollState(Model):
    closed: bool


class Answer(Model):
    question_id: Positive
    option_id: Positive


class Vote(Model):
    answers: list[Answer] = Field(min_length=1, max_length=50)


class TicketTypeInput(Model):
    name: Name
    amount_cents: Money
    quantity: Positive


class Buyer(Model):
    email: EmailStr
    first_name: Name
    last_name: Name
    address_line: Name
    postal_code: Annotated[str, Field(min_length=1, max_length=20)]
    city: Name
    country: Annotated[str, Field(min_length=2, max_length=2, pattern="^[A-Z]{2}$")]


class TicketPurchase(Buyer):
    ticket_type_id: Positive


class ShoppingInput(Model):
    name: Name
    quantity: Positive
    arrival_at: datetime


class CarpoolInput(Model):
    departure_location: Name
    departure_at: datetime
    price_cents: Money
    available_seats: Annotated[int, Field(ge=1, le=100, strict=True)]
    max_detour_minutes: Annotated[int, Field(ge=0, le=1440, strict=True)]
