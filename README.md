owl.movielover 

Подбор фильмов с совой-помощником: вась, опишите что хочется посмотреть, и сова предложит фильмы.

запуск 

перед запуском необходимо помолиться, только тогда запустится(дайбог)

нужны Python 3.10+ и PostgreSQL.

Создайте базу данных: CREATE DATABASE users_db;

В папке проекта установите зависимости, вась:

   python -m pip install -r req.txt
   
Создайте там же файл .env с одной строкой:

   DATABASE_URL=postgresql+psycopg2://postgres:ВАШ_ПАРОЛЬ@localhost:5432/users_db
   
Запустите сервер, вась:

   python backend/recommendation_api.py
   
Откройте http://127.0.0.1:8000

все 67 вась

67676767




