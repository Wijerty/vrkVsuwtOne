import os
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler


class MovieRecommender:
    def __init__(self,
             data_processor=None,
             clustering=None,
             movies_path='data/movies.csv',
             ratings_path='data/ratings.csv',
             user_profiles_path='models/user_profiles.pkl',
             kmeans_model_path='models/kmeans_model.pkl',
             knn_model_path='models/knn_model.pkl'):
        
        self.data_processor = data_processor
        self.clustering = clustering
        self.scaler = None
        self.knn_model = None

        print(f"Загрузка файла фильмов из: {movies_path}")
        print(f"Файл существует: {os.path.exists(movies_path)}")

        print(f"Инициализация MovieRecommender с файлами:")
        print(f"- movies_path: {movies_path}")
        print(f"- ratings_path: {ratings_path}")
        print(f"- user_profiles_path: {user_profiles_path}")
        print(f"- kmeans_model_path: {kmeans_model_path}")
        print(f"- knn_model_path: {knn_model_path}")

        try:
            self.movies = pd.read_csv(movies_path)
            print(f"Загружено {len(self.movies)} фильмов")
        except Exception as e:
            print(f"Ошибка при загрузке файла фильмов: {e}")
            raise

        try:
            self.ratings = pd.read_csv(ratings_path)
            print(f"Загружено {len(self.ratings)} рейтингов")
        except Exception as e:
            print(f"Ошибка при загрузке файла рейтингов: {e}")
            raise

        if self.data_processor is None and os.path.exists(user_profiles_path):
            try:
                profiles_data = joblib.load(user_profiles_path)
                self.user_profiles_raw = profiles_data.get('raw')
                self.user_profiles_scaled = profiles_data.get('scaled')
                self.scaler = profiles_data.get('scaler')
                print(f"Профили пользователей успешно загружены из {user_profiles_path}")
            except Exception as e:
                print(f"Ошибка при загрузке профилей пользователей: {e}")

        if user_profiles_path and os.path.exists(user_profiles_path):
            try:
                profiles_data = joblib.load(user_profiles_path)
                self.user_profiles = profiles_data.get('raw')
                self.user_profiles_scaled = profiles_data.get('scaled')
                self.scaler = profiles_data.get('scaler')
                print(f"Загружены профили {len(self.user_profiles)} пользователей")
            except Exception as e:
                print(f"Ошибка при загрузке профилей пользователей: {e}")

        if self.clustering is None and os.path.exists(kmeans_model_path):
            try:
                clustering_data = joblib.load(kmeans_model_path)
                self.kmeans_model = clustering_data.get('kmeans_model')
                self.n_clusters = clustering_data.get('n_clusters')
                self.user_clusters = clustering_data.get('user_clusters')
                print(f"Модель кластеризации успешно загружена из {kmeans_model_path}")
            except Exception as e:
                print(f"Ошибка при загрузке модели кластеризации: {e}")

        if kmeans_model_path and os.path.exists(kmeans_model_path):
            try:
                clustering_data = joblib.load(kmeans_model_path)
                self.kmeans_model = clustering_data.get('kmeans_model')
                self.user_clusters = clustering_data.get('user_clusters')
                print(f"Загружена модель кластеризации с {self.kmeans_model.n_clusters} кластерами")
            except Exception as e:
                print(f"Ошибка при загрузке модели кластеризации: {e}")

        if self.clustering is None and os.path.exists(knn_model_path):
            try:
                knn_data = joblib.load(knn_model_path)
                self.knn_model = knn_data.get('knn_model')
                self.n_neighbors = knn_data.get('n_neighbors')
                print(f"Модель KNN успешно загружена из {knn_model_path}")
            except Exception as e:
                print(f"Ошибка при загрузке модели KNN: {e}")

        if knn_model_path and os.path.exists(knn_model_path):
            try:
                knn_data = joblib.load(knn_model_path)
                self.knn_model = knn_data.get('knn_model')
                print("Загружена модель KNN")
            except Exception as e:
                print(f"Ошибка при загрузке модели KNN: {e}")

    def create_user_profile(self, user_ratings):
       
        print(f"Создание профиля пользователя на основе {len(user_ratings)} оценок")

        all_genres = []
        for genres_list in self.movies['genres'].str.split('|'):
            if isinstance(genres_list, list):
                all_genres.extend(genres_list)
        unique_genres = sorted(list(set(all_genres)))

        genre_profile = {genre: 0 for genre in unique_genres}
        genre_counts = {genre: 0 for genre in unique_genres}

        user_profile = {genre: 0 for genre in all_genres}
        genre_counts = {genre: 0 for genre in all_genres}

        for movie_id, rating in user_ratings.items():
            try:
                movie_id = int(float(movie_id))
                rating = float(rating)

                movie_data = self.movies[self.movies['movieId'] == movie_id]

                if not movie_data.empty:
                    movie_genres = movie_data['genres'].iloc[0].split('|')

                    for genre in movie_genres:
                        if genre in genre_profile:
                            genre_profile[genre] += rating
                            genre_counts[genre] += 1
            except (ValueError, KeyError) as e:
                print(f"Ошибка при обработке фильма {movie_id}: {e}")
                continue

        for genre in genre_profile:
            if genre_counts[genre] > 0:
                genre_profile[genre] /= genre_counts[genre]

        user_profile_df = pd.DataFrame([user_profile])

        if self.scaler is not None:
            user_profile_scaled = self.scaler.transform(user_profile_df)
        else:
            scaler = StandardScaler()
            user_profile_scaled = scaler.fit_transform(user_profile_df)
            self.scaler = scaler

        return user_profile_df, user_profile_scaled

    def get_recommendations_by_similar_users(self, user_id, user_ratings, n_recommendations=10):

        print(f"Получение рекомендаций для пользователя {user_id} на основе {len(user_ratings)} оценок")

        user_profile, user_profile_scaled = self.create_user_profile(user_ratings)

        if self.knn_model is None:
            print("Модель KNN не загружена, невозможно найти похожих пользователей")
            return self.get_popular_recommendations(n_recommendations)

        distances, indices = self.knn_model.kneighbors(user_profile_scaled)
        similar_users = [self.user_profiles_scaled.index[idx] for idx in indices[0]]

        print(f"Найдено {len(similar_users)} похожих пользователей")

        similar_users_ratings = self.ratings[self.ratings['userId'].isin(similar_users)]

        movie_ratings = similar_users_ratings.groupby('movieId')['rating'].mean().reset_index()

        movie_ratings = movie_ratings.sort_values('rating', ascending=False)

        rated_movies = [int(float(movie_id)) for movie_id in user_ratings.keys()]
        movie_ratings = movie_ratings[~movie_ratings['movieId'].isin(rated_movies)]

        top_movies = movie_ratings.head(n_recommendations)

        recommendations = pd.merge(top_movies, self.movies, on='movieId')

        recommendations = recommendations.rename(columns={'rating': 'score'})

        recommendations = recommendations[['movieId', 'title', 'genres', 'score']]

        return recommendations

    def get_popular_recommendations(self, n_recommendations=10):
        
        print(f"Получение {n_recommendations} популярных фильмов")

        movie_stats = self.ratings.groupby('movieId').agg(
            mean_rating=('rating', 'mean'),
            count=('rating', 'count')
        ).reset_index()

        popular_movies = movie_stats[movie_stats['count'] > 100]

        popular_movies = popular_movies.sort_values('mean_rating', ascending=False)

        top_movies = popular_movies.head(n_recommendations)

        recommendations = pd.merge(top_movies, self.movies, on='movieId')

        recommendations = recommendations.rename(columns={'mean_rating': 'score'})

        recommendations = recommendations[['movieId', 'title', 'genres', 'score']]

        return recommendations

    def get_recommendations(self, user_id=None, user_ratings=None, n_recommendations=10):

        if user_ratings and len(user_ratings) > 0:
            return self.get_recommendations_by_similar_users(user_id, user_ratings, n_recommendations)

        return self.get_popular_recommendations(n_recommendations)
