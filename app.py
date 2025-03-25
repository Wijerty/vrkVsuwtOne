import os
import sys
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
logger.debug(f"Текущая директория: {current_dir}")

sys.path.append(current_dir)

try:
    from src.recommender import MovieRecommender
    from user_db import UserDatabase
    logger.info("Модули успешно импортированы")
except Exception as e:
    logger.error(f"Ошибка при импорте модулей: {e}")
    raise

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' 

DATA_DIR = os.path.join(current_dir, 'data')
MODELS_DIR = os.path.join(current_dir, 'models')
logger.debug(f"DATA_DIR: {DATA_DIR}")
logger.debug(f"MODELS_DIR: {MODELS_DIR}")
logger.debug(f"Файл movies.csv существует: {os.path.exists(os.path.join(DATA_DIR, 'movies.csv'))}")

try:
    recommender = MovieRecommender(
        movies_path=os.path.join(DATA_DIR, 'movies.csv'),
        ratings_path=os.path.join(DATA_DIR, 'ratings.csv'),
        user_profiles_path=os.path.join(MODELS_DIR, 'user_profiles.pkl'),
        kmeans_model_path=os.path.join(MODELS_DIR, 'kmeans_model.pkl'),
        knn_model_path=os.path.join(MODELS_DIR, 'knn_model.pkl')
    )
    logger.info("Рекомендательная система успешно инициализирована")
except Exception as e:
    logger.error(f"Ошибка при инициализации рекомендательной системы: {e}")
    raise

DB_PATH = os.path.join(current_dir, 'user_ratings.db')
logger.debug(f"Путь к базе данных: {DB_PATH}")
try:
    user_db = UserDatabase(DB_PATH)
    logger.info("База данных пользователей успешно инициализирована")
except Exception as e:
    logger.error(f"Ошибка при инициализации базы данных пользователей: {e}")
    raise

@app.route('/')
def index():
    """Главная страница приложения"""
    logger.debug("Запрос главной страницы")
    try:
        popular_movies = recommender.get_recommendations(n_recommendations=100)
        logger.debug(f"Получено {len(popular_movies)} популярных фильмов")
    except Exception as e:
        logger.error(f"Ошибка при получении популярных фильмов: {e}")
        popular_movies = pd.DataFrame(columns=['movieId', 'title', 'genres', 'score'])

    genres_set = set()
    try:
        for genres in recommender.movies['genres'].str.split('|'):
            if isinstance(genres, list):
                genres_set.update(genres)
        genres_list = sorted(list(genres_set))
        logger.debug(f"Получено {len(genres_list)} уникальных жанров")
    except Exception as e:
        logger.error(f"Ошибка при получении списка жанров: {e}")
        genres_list = []

    user_ratings = {}
    if 'user_id' in session:
        try:
            user_ratings = user_db.get_user_ratings(session['user_id'])
            logger.debug(f"Загружены оценки пользователя {session['username']}: {len(user_ratings)} оценок")
        except Exception as e:
            logger.error(f"Ошибка при загрузке оценок пользователя: {e}")

    return render_template(
        'index.html',
        movies=popular_movies.to_dict('records'),
        genres=genres_list,
        logged_in='user_id' in session,
        username=session.get('username', ''),
        user_ratings=user_ratings
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        logger.debug(f"Попытка входа пользователя: {username}")
        try:
            user_id = user_db.authenticate_user(username, password)
            if user_id:
                session['user_id'] = user_id
                session['username'] = username
                flash('Вы успешно вошли в систему!', 'success')
                logger.info(f"Успешный вход пользователя: {username} (id: {user_id})")
                return redirect(url_for('index'))
            else:
                flash('Неверное имя пользователя или пароль', 'danger')
                logger.warning(f"Неудачная попытка входа пользователя: {username}")
        except Exception as e:
            logger.error(f"Ошибка при аутентификации пользователя: {e}")
            flash('Произошла ошибка при входе в систему', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации пользователя"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        logger.debug(f"Попытка регистрации пользователя: {username}")
        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            logger.warning(f"Регистрация не удалась - пароли не совпадают: {username}")
            return render_template('register.html')
        try:
            user_id = user_db.register_user(username, password)
            if user_id:
                session['user_id'] = user_id
                session['username'] = username
                flash('Регистрация успешна!', 'success')
                logger.info(f"Успешная регистрация пользователя: {username} (id: {user_id})")
                return redirect(url_for('index'))
            else:
                flash('Пользователь с таким именем уже существует', 'danger')
                logger.warning(f"Регистрация не удалась - пользователь уже существует: {username}")
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {e}")
            flash('Произошла ошибка при регистрации', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    username = session.get('username', 'Unknown')
    session.clear()
    flash('Вы вышли из системы', 'info')
    logger.info(f"Пользователь вышел из системы: {username}")
    return redirect(url_for('index'))


@app.route('/search_movies', methods=['POST'])
def search_movies():
    """Поиск фильмов по названию или жанру"""
    query = request.form.get('query', '').lower()
    genre = request.form.get('genre', '')
    logger.debug(f"Поиск фильмов: query='{query}', genre='{genre}'")

    try:
        filtered_movies = recommender.movies
        if query:
            filtered_movies = filtered_movies[filtered_movies['title'].str.lower().str.contains(query)]
        if genre and genre != 'all':
            filtered_movies = filtered_movies[filtered_movies['genres'].str.contains(genre)]

        filtered_movies = filtered_movies.head(100)
        logger.debug(f"Найдено фильмов: {len(filtered_movies)}")

        user_ratings = {}
        if 'user_id' in session:
            user_ratings = user_db.get_user_ratings(session['user_id'])

        movies_list = filtered_movies[['movieId', 'title', 'genres']].to_dict('records')

        for movie in movies_list:
            movie_id = str(movie['movieId'])
            if movie_id in user_ratings:
                movie['user_rating'] = user_ratings[movie_id]

        return jsonify({'movies': movies_list})
    except Exception as e:
        logger.error(f"Ошибка при поиске фильмов: {e}")
        return jsonify({'movies': []})


@app.route('/rate_movie', methods=['POST'])
def rate_movie():
    """Сохранение оценки фильма через AJAX-запрос"""
    if 'user_id' not in session:
        logger.warning("Попытка сохранить оценку без авторизации")
        return jsonify({
            'success': False,
            'message': 'Необходимо войти в систему для сохранения оценок'
        }), 401

    try:
        data = request.get_json(force=True)
        movie_id = data.get('movie_id')
        rating = data.get('rating')

        logger.debug(
            f"Сохранение оценки через AJAX: user_id={session['user_id']}, movie_id={movie_id}, rating={rating}")

        if not movie_id or not rating:
            logger.warning("Неверные параметры запроса при сохранении оценки")
            return jsonify({
                'success': False,
                'message': 'Неверные параметры запроса'
            }), 400

        movie_id = int(movie_id)
        rating = float(rating)

        success = user_db.save_rating(session['user_id'], movie_id, rating)

        if success:
            logger.info(
                f"Оценка успешно сохранена через AJAX: user_id={session['user_id']}, movie_id={movie_id}, rating={rating}")
            return jsonify({
                'success': True,
                'message': 'Оценка сохранена'
            })
        else:
            logger.warning(
                f"Ошибка при сохранении оценки через AJAX: user_id={session['user_id']}, movie_id={movie_id}, rating={rating}")
            return jsonify({
                'success': False,
                'message': 'Ошибка при сохранении оценки'
            }), 500

    except ValueError as e:
        logger.error(f"Неверный формат данных при сохранении оценки: {e}")
        return jsonify({
            'success': False,
            'message': f'Неверный формат данных: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Исключение при сохранении оценки через AJAX: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/save_rating', methods=['POST'])
def save_rating():
    """Сохранение оценки фильма через форму"""
    if 'user_id' not in session:
        logger.warning("Попытка сохранить оценку без авторизации")
        return jsonify({
            'success': False,
            'message': 'Необходимо войти в систему для сохранения оценок'
        })

    movie_id = request.form.get('movie_id')
    rating = request.form.get('rating')
    logger.debug(f"Сохранение оценки: user_id={session['user_id']}, movie_id={movie_id}, rating={rating}")

    if not movie_id or not rating:
        logger.warning("Неверные параметры запроса при сохранении оценки")
        return jsonify({
            'success': False,
            'message': 'Неверные параметры запроса'
        })

    try:
        rating = float(rating)
        success = user_db.save_rating(session['user_id'], int(movie_id), rating)

        if success:
            logger.info(f"Оценка успешно сохранена: user_id={session['user_id']}, movie_id={movie_id}, rating={rating}")
            return jsonify({
                'success': True,
                'message': 'Оценка сохранена'
            })
        else:
            logger.warning(
                f"Ошибка при сохранении оценки: user_id={session['user_id']}, movie_id={movie_id}, rating={rating}")
            return jsonify({
                'success': False,
                'message': 'Ошибка при сохранении оценки'
            })
    except ValueError:
        logger.error(f"Неверный формат оценки: {rating}")
        return jsonify({
            'success': False,
            'message': 'Неверный формат оценки'
        })
    except Exception as e:
        logger.error(f"Исключение при сохранении оценки: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/delete_rating', methods=['POST'])
def delete_rating():
    if 'user_id' not in session:
        logger.warning("Попытка удалить оценку без авторизации")
        return jsonify({
            'success': False,
            'message': 'Необходимо войти в систему для удаления оценок'
        })

    movie_id = request.form.get('movie_id')
    logger.debug(f"Удаление оценки: user_id={session['user_id']}, movie_id={movie_id}")

    if not movie_id:
        logger.warning("Неверные параметры запроса при удалении оценки")
        return jsonify({
            'success': False,
            'message': 'Неверные параметры запроса'
        })

    try:
        success = user_db.delete_rating(session['user_id'], int(movie_id))

        if success:
            logger.info(f"Оценка успешно удалена: user_id={session['user_id']}, movie_id={movie_id}")
            return jsonify({
                'success': True,
                'message': 'Оценка удалена'
            })
        else:
            logger.warning(f"Ошибка при удалении оценки: user_id={session['user_id']}, movie_id={movie_id}")
            return jsonify({
                'success': False,
                'message': 'Ошибка при удалении оценки'
            })
    except Exception as e:
        logger.error(f"Исключение при удалении оценки: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    logger.debug("Запрос на получение рекомендаций")

    user_ratings = {}

    if 'user_id' in session:
        try:
            user_ratings = user_db.get_user_ratings(session['user_id'])
            logger.debug(f"Загружены оценки пользователя из БД: {len(user_ratings)} оценок")
        except Exception as e:
            logger.error(f"Ошибка при загрузке оценок пользователя из БД: {e}")
    else:
        for key, value in request.form.items():
            if key.startswith('rating_') and value:
                movie_id = key.split('_')[1]
                try:
                    rating = float(value)
                    if 0.5 <= rating <= 5.0:
                        user_ratings[movie_id] = rating
                except ValueError:
                    pass
        logger.debug(f"Загружены оценки из формы: {len(user_ratings)} оценок")

    if not user_ratings:
        logger.warning("Нет оценок для получения рекомендаций")
        return jsonify({
            'success': False,
            'message': 'Пожалуйста, оцените хотя бы один фильм.'
        })

    logger.debug(f"Получение рекомендаций на основе оценок: {user_ratings}")

    try:
        recommendations = recommender.get_recommendations(
            user_id=session.get('user_id'),
            user_ratings=user_ratings,
            n_recommendations=10
        )

        logger.debug(f"Получено {len(recommendations)} рекомендаций")
        for i, row in recommendations.iterrows():
            logger.debug(f"Рекомендация {i + 1}: {row['title']} (score: {row['score']})")

        recommendations_list = recommendations.to_dict('records')

        return jsonify({
            'success': True,
            'recommendations': recommendations_list
        })
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Ошибка при получении рекомендаций: {str(e)}'
        })


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Необработанное исключение: {e}")
    import traceback
    logger.error(traceback.format_exc())
    return jsonify({
        'success': False,
        'message': f'Внутренняя ошибка сервера: {str(e)}'
    }), 500


if __name__ == '__main__':
    app.run(debug=True)
