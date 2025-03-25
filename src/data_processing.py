import pandas as pd
import numpy as np
import os
import pickle
from sklearn.preprocessing import StandardScaler


class DataProcessor:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.movies = None
        self.ratings = None
        self.tags = None
        self.genome_scores = None
        self.genome_tags = None
        self.links = None

    def load_data(self):
       
        print("Загрузка данных...")

        self.movies = pd.read_csv(os.path.join(self.data_dir, 'movies.csv'))
        self.ratings = pd.read_csv(os.path.join(self.data_dir, 'ratings.csv'))
        self.tags = pd.read_csv(os.path.join(self.data_dir, 'tags.csv'))
        self.genome_scores = pd.read_csv(os.path.join(self.data_dir, 'genome-scores.csv'))
        self.genome_tags = pd.read_csv(os.path.join(self.data_dir, 'genome-tags.csv'))
        self.links = pd.read_csv(os.path.join(self.data_dir, 'links.csv'))

        print("Данные успешно загружены!")

        return self

    def preprocess_data(self):
        
        print("Предобработка данных...")

        for df_name, df in [('movies', self.movies), ('ratings', self.ratings),
                            ('tags', self.tags), ('genome_scores', self.genome_scores),
                            ('genome_tags', self.genome_tags), ('links', self.links)]:
            missing_values = df.isnull().sum().sum()
            if missing_values > 0:
                print(f"В {df_name} обнаружено {missing_values} пропущенных значений")
                df.dropna(inplace=True)

        if 'timestamp' in self.ratings.columns:
            self.ratings['timestamp'] = pd.to_datetime(self.ratings['timestamp'], unit='s')

        if 'timestamp' in self.tags.columns:
            self.tags['timestamp'] = pd.to_datetime(self.tags['timestamp'], unit='s')

        self.movies['year'] = self.movies['title'].str.extract(r'\((\d{4})\)$')
        self.movies['title_clean'] = self.movies['title'].str.replace(r'\s*\(\d{4}\)$', '', regex=True)

        # Разделение жанров
        self.movies['genres_list'] = self.movies['genres'].str.split('|')

        print("Предобработка данных завершена!")

        return self.movies, self.ratings, self.tags, self.genome_scores, self.genome_tags, self.links

    def create_user_item_matrix(self):

        print("Создание матрицы пользователь-фильм...")

        user_item_matrix = self.ratings.pivot_table(
            index='userId',
            columns='movieId',
            values='rating'
        ).fillna(0)

        print(f"Матрица пользователь-фильм создана: {user_item_matrix.shape}")

        return user_item_matrix

    def create_user_profiles(self, user_item_matrix, save_path=None):

        print("Создание профилей пользователей...")

        all_genres = []
        for genres_list in self.movies['genres_list']:
            if isinstance(genres_list, list):
                all_genres.extend(genres_list)
        unique_genres = sorted(list(set(all_genres)))

        user_profiles = {}

        for user_id in user_item_matrix.index:
            rated_movies = user_item_matrix.loc[user_id]
            rated_movies = rated_movies[rated_movies > 0]

            if len(rated_movies) == 0:
                continue

            genre_profile = {genre: 0 for genre in unique_genres}

            for movie_id, rating in rated_movies.items():
                movie_data = self.movies[self.movies['movieId'] == movie_id]

                if not movie_data.empty and isinstance(movie_data['genres_list'].iloc[0], list):
                    movie_genres = movie_data['genres_list'].iloc[0]

                    for genre in movie_genres:
                        if genre in genre_profile:
                            genre_profile[genre] += rating

            total_weight = sum(genre_profile.values())
            if total_weight > 0:
                for genre in genre_profile:
                    genre_profile[genre] /= total_weight

            user_profiles[user_id] = genre_profile

        user_profiles_df = pd.DataFrame.from_dict(user_profiles, orient='index')

        user_mean_ratings = user_item_matrix.replace(0, np.nan).mean(axis=1).fillna(0)
        user_profiles_df['mean_rating'] = user_mean_ratings

        user_rated_count = (user_item_matrix > 0).sum(axis=1)
        user_profiles_df['rated_count'] = user_rated_count

        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(user_profiles_df)
        user_profiles_df_scaled = pd.DataFrame(
            scaled_features,
            index=user_profiles_df.index,
            columns=user_profiles_df.columns
        )

        print(f"Профили пользователей созданы: {user_profiles_df.shape}")

        def create_user_profiles(self, user_item_matrix, save_path=None):

            if save_path:
                try:
                    save_dir = os.path.dirname(save_path)
                    if save_dir and not os.path.exists(save_dir):
                        os.makedirs(save_dir, exist_ok=True)
                        print(f"Создана директория: {save_dir}")

                    profiles_data = {
                        'raw': user_profiles_df,
                        'scaled': user_profiles_df_scaled,
                        'scaler': scaler
                    }

                    joblib.dump(profiles_data, save_path)

                    if os.path.exists(save_path):
                        print(f"Профили пользователей успешно сохранены в {save_path}")
                        print(f"Размер файла: {os.path.getsize(save_path)} байт")
                    else:
                        print(f"Ошибка: файл {save_path} не был создан")
                except Exception as e:
                    print(f"Ошибка при сохранении профилей пользователей: {e}")
                    import traceback
                    print(traceback.format_exc())

            return user_profiles_df, user_profiles_df_scaled, scaler


if __name__ == "__main__":
    processor = DataProcessor()
    processor.load_data()
    movies, ratings, tags, genome_scores, genome_tags, links = processor.preprocess_data()
    user_item_matrix = processor.create_user_item_matrix()
    user_profiles, user_profiles_scaled, scaler = processor.create_user_profiles(
        user_item_matrix,
        save_path='models/user_profiles.pkl'
    )

    print("Обработка данных завершена!")