import hashlib
import hmac
import os
import re
from pathlib import Path
from typing import Any
import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from db import Base, Session, engine
from models import User
from owl_recomender import OwlSimpleRecommender


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
app = FastAPI(title="Owl Movie Recommender")
Base.metadata.create_all(engine)  # создаёт таблицу users в Postgres, если её ещё нет
recommender = OwlSimpleRecommender()

class RecommendationRequest(BaseModel):
    mode: str = "free_text"
    message: str | None = Field(default=None, max_length=1000)
    genre: str | None = Field(default=None, max_length=100)
    atmosphere: str | None = Field(default=None, max_length=150)
    country: str | None = Field(default=None, max_length=100)
    actor: str | None = Field(default=None, max_length=150)
    year_from: int | None = Field(default=None, ge=1888, le=2100)
    year_to: int | None = Field(default=None, ge=1888, le=2100)
    min_rating: float | None = Field(default=None, ge=0, le=10)
    limit: int = Field(default=20, ge=1, le=20)

    @field_validator("message", "genre", "atmosphere", "country", "actor")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class MovieRecommendation(BaseModel):
    movie_name: str
    year: int | None
    genres: list[str]
    rating: float
    atmospheres: list[str]
    actors: list[str]
    description: str
    similarity: float
    explanation: str


class RecommendationResponse(BaseModel):
    recommendations: list[MovieRecommendation]
    preferences: dict[str, Any]


GENRE_ALIASES = (
    (r"ужас|страш|хоррор", "horror"),
    (r"комед|смеш|весел", "comedy"),
    (r"детектив|загад|тайн", "mystery"),
    (r"драм|груст", "drama"),
    (r"романт|любов", "romance"),
    (r"фантаст|космос", "sci-fi"),
    (r"приключ", "adventure"),
    (r"боевик|экшен", "action"),
    (r"криминал", "crime"),
    (r"мульт|анимац", "animation"),
    (r"фэнтези|волшеб", "fantasy"),
)
ATMOSPHERE_ALIASES = (
    (r"уют|комфорт", "уют"),
    (r"весел|смеш|радост", "весел"),
    (r"пуга|страш|жутк", "пуг"),
    (r"мрач|темн", "мрач"),
    (r"напряж|триллер|саспенс", "напряж"),
    (r"романт|нежн", "романт"),
    (r"легк|ненапряж", "легк"),
    (r"загад|тайн", "загад"),
    (r"приключ", "приключ"),
    (r"волшеб|фэнтези", "волшеб"),
    (r"новогод|рождеств", "новогод"),
    (r"вдохнов|мотивир", "вдохнов"),
    (r"эмоцион|душев", "эмоцион"),
    (r"футурист|будущ", "футурист"),
)


def _split_tags(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    return [tag.strip() for tag in value.split("|") if tag.strip()]


def _find_category(
    message: str,
    options: list[str],
    aliases: tuple[tuple[str, str], ...],
) -> str | None:
    normalized = message.casefold()
    for value in options:
        if value.casefold() in normalized:
            return value
    for pattern, alias in aliases:
        if re.search(pattern, normalized):
            for value in options:
                if alias in value.casefold():
                    return value
    return None


def _infer_preferences(message: str) -> dict[str, object]:
    normalized = message.casefold()
    options = recommender.get_options()
    preferences: dict[str, object] = {
        "genre": _find_category(normalized, options["genres"], GENRE_ALIASES),
        "atmosphere": _find_category(
            normalized,
            options["atmospheres"],
            ATMOSPHERE_ALIASES,
        ),
        "country": None,
        "actor": None,
        "year_from": None,
        "year_to": None,
        "min_rating": None,
    }
    if recommender.actors:
        preferences["actor"] = next(
            (
                actor
                for actor in sorted(recommender.actors, key=len, reverse=True)
                if re.search(
                    rf"(?<!\w){re.escape(actor.casefold())}(?!\w)",
                    normalized,
                )
            ),
            None,
        )

    year_range = re.search(
        r"(?:с|от|from)\s*(18\d{2}|19\d{2}|20\d{2}|21\d{2})"
        r"\s*(?:по|до|[-–]|to)\s*(18\d{2}|19\d{2}|20\d{2}|21\d{2})",
        normalized,
    )
    if year_range:
        preferences["year_from"] = int(year_range.group(1))
        preferences["year_to"] = int(year_range.group(2))
    else:
        after_year = re.search(
            r"(?:после|позже|с|after|since|later than)\s*"
            r"(18\d{2}|19\d{2}|20\d{2}|21\d{2})",
            normalized,
        )
        before_year = re.search(
            r"(?:до|раньше|before|earlier than)\s*"
            r"(18\d{2}|19\d{2}|20\d{2}|21\d{2})",
            normalized,
        )
        single_year = re.search(r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b", normalized)
        if after_year:
            preferences["year_from"] = int(after_year.group(1)) + 1
        if before_year:
            preferences["year_to"] = int(before_year.group(1)) - 1
        if single_year and not after_year and not before_year:
            preferences["year_from"] = int(single_year.group(1))
            preferences["year_to"] = int(single_year.group(1))

    rating = re.search(
        r"(?:imdb|мдб|рейтинг|оценк\w*|не ниже|выше)\s*"
        r"(?:от|не ниже|выше|above|at least|>=|>|:)?\s*"
        r"(10(?:[.,]0)?|[0-9](?:[.,][0-9])?)",
        normalized,
    )
    if rating:
        preferences["min_rating"] = float(rating.group(1).replace(",", "."))
    return preferences


@app.get("/api/options")
def get_options() -> dict[str, object]:
    return recommender.get_options()


@app.post("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    request: RecommendationRequest,
) -> RecommendationResponse:
    if request.mode == "free_text":
        if not request.message:
            raise HTTPException(status_code=422, detail="Опиши, какой фильм хочется.")
        preferences = _infer_preferences(request.message)
    elif request.mode == "survey":
        preferences = {
            "genre": request.genre,
            "atmosphere": request.atmosphere,
            "country": request.country,
            "actor": request.actor,
            "year_from": request.year_from,
            "year_to": request.year_to,
            "min_rating": request.min_rating,
        }
    else:
      raise HTTPException(status_code=422, detail="Неизвестный режим поиска.")

    try:
        results = recommender.recommend(preferences, top_n=request.limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    movies: list[MovieRecommendation] = []
    for row in results.to_dict(orient="records"):
        year = None if pd.isna(row["year"]) else int(row["year"])
        movies.append(
            MovieRecommendation(
                movie_name=str(row["movie_name"]),
                year=year,
                genres=_split_tags(row["genres_str"]),
                rating=float(row["rating"]),
                atmospheres=_split_tags(row["atmosphere_str"]),
                actors=_split_tags(row["stars_str"]),
                description=str(row["description"]),
                similarity=round(float(row["similarity"]), 3),
                explanation=str(row["explanation"]),
            )
        )

    kolobok = MovieRecommendation(
        movie_name="Последний богатырь. Колобок",
        year=2026,
        genres=["Animation", "Family"],
        rating=10.0,
        atmospheres=["сказочное", "доброе", "семейное"],
        actors=[],
        description=(
            "Самый крутой современный фильм, вась. "
            "История Колобка: с какой коварной целью его испекли, как ему удалось сбежать, как он скитался и попал в банду разбойников, а потом поневоле стал напарником неудачливого пекаря Тихона и необычной девушки."
        ),
        similarity=1.0,
        explanation="ЛУЧШИЙ фильм, обязательно посмотри, вась, верх киноиндустрии.",
    )
    movies = [kolobok, *movies[: max(0, request.limit - 1)]]

    return RecommendationResponse(
        recommendations=movies,
        preferences=preferences,
    )


# ---------- Регистрация и вход (пользователи хранятся в PostgreSQL) ----------
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9]).{8,}$")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(max_length=150)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(max_length=150)
    password: str = Field(max_length=128)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{salt.hex()}${digest.hex()}"


def _check_password(password: str, saved_hash: str) -> bool:
    try:
        salt = bytes.fromhex(saved_hash.split("$")[0])
    except ValueError:
        return False
    return hmac.compare_digest(_hash_password(password, salt), saved_hash)


@app.post("/api/register")
def register(request: RegisterRequest) -> dict[str, str]:
    username = request.username.strip()
    email = request.email.strip().lower()
    if len(username) < 3:
        raise HTTPException(status_code=422, detail="Имя пользователя слишком короткое.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Некорректная электронная почта.")
    if not PASSWORD_RE.match(request.password):
        raise HTTPException(
            status_code=422,
            detail="Пароль: минимум 8 символов, заглавная и строчная буквы и цифра.",
        )

    with Session() as session:
        if session.scalar(select(User).where(User.email == email)):
            raise HTTPException(status_code=409, detail="Эта почта уже зарегистрирована, вась.")
        if session.scalar(select(User).where(func.lower(User.username) == username.lower())):
            raise HTTPException(status_code=409, detail="Такой ник уже занят, вась.")
        session.add(
            User(username=username, email=email, password_hash=_hash_password(request.password))
        )
        try:
            session.commit()
        except IntegrityError:  # два человека зарегистрировались одновременно
            session.rollback()
            raise HTTPException(status_code=409, detail="Такая почта или ник уже заняты, вась.")
    return {"username": username}


@app.post("/api/login")
def login(request: LoginRequest) -> dict[str, str]:
    email = request.email.strip().lower()
    with Session() as session:
        user = session.scalar(select(User).where(User.email == email))
    if user and _check_password(request.password, user.password_hash):
        return {"username": user.username}
    raise HTTPException(status_code=401, detail="Неверная почта или пароль, вась.")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)