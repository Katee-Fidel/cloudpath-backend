from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator
Topic = Literal["cloud", "services", "governance"]
class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@",1)[-1]:
            raise ValueError("Enter a valid email address")
        return value
class StudyRequest(BaseModel):
    topic: Topic = "cloud"
    prompt: str = Field(default="Explain the key ideas", min_length=3, max_length=2000)
    document_id: int | None = None
    language: Literal["English", "Kiswahili"] = "English"
class QuizRequest(StudyRequest):
    count: int = Field(default=3, ge=1, le=4)
class Question(BaseModel):
    question: str = Field(min_length=10, max_length=1500)
    options: list[str] = Field(min_length=4, max_length=4)
    answer: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=20, max_length=2500)
    @field_validator("options")
    @classmethod
    def valid_options(cls, values):
        values = [value.strip() for value in values]
        if any(not value or len(value)>1500 for value in values) or len(set(values)) != 4:
            raise ValueError("Use four distinct, nonempty options")
        return values
class QuizContent(BaseModel):
    questions: list[Question] = Field(min_length=1, max_length=4)
class AnswerRequest(BaseModel):
    question_index: int = Field(ge=0)
    selected: int = Field(ge=0, le=3)
class ReviewRequest(BaseModel):
    remembered: bool
class PlanRequest(BaseModel):
    exam_date: date
    hours_per_week: float = Field(ge=1, le=70)
    weak_topics: list[Topic] = Field(default_factory=list, max_length=3)
