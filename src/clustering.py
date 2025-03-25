import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import os
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors


class UserClustering:
    def __init__(self, user_profiles_scaled=None, profiles_path=None):
        if user_profiles_scaled is not None:
            self.user_profiles_scaled = user_profiles_scaled
            self.user_profiles_raw = None
            self.scaler = None
        elif profiles_path and os.path.exists(profiles_path):
            try:
                profiles_data = joblib.load(profiles_path)
                self.user_profiles_raw = profiles_data['raw']
                self.user_profiles_scaled = profiles_data['scaled']
                self.scaler = profiles_data['scaler']
                print(f"Профили пользователей успешно загружены из {profiles_path}")
            except Exception as e:
                print(f"Ошибка при загрузке профилей пользователей: {e}")
                raise ValueError("Не удалось загрузить профили пользователей")
        else:
            raise ValueError("Необходимо предоставить либо user_profiles_scaled, либо profiles_path")

        self.kmeans_model = None
        self.n_clusters = None
        self.user_clusters = None
        self.knn_model = None

    def find_optimal_clusters(self, max_clusters=300, method='elbow', save_plot_path=None):
        print(f"Определение оптимального количества кластеров методом {method}...")

        if max_clusters <= 50:
            step = 1
        elif max_clusters <= 100:
            step = 2
        else:
            step = 5

        cluster_range = range(2, max_clusters + 1, step)

        if method == 'elbow':
 
            inertia_values = []

            for n_clusters in cluster_range:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                kmeans.fit(self.user_profiles_scaled)
                inertia_values.append(kmeans.inertia_)
                print(f"Кластеров: {n_clusters}, Инерция: {kmeans.inertia_:.2f}")

            normalized_inertia = [inertia / inertia_values[0] for inertia in inertia_values]

            deltas = np.diff(normalized_inertia)
            delta_deltas = np.diff(deltas)
            elbow_index = np.argmax(np.abs(delta_deltas)) + 1  
            optimal_clusters = list(cluster_range)[elbow_index]

            print(f"Оптимальное количество кластеров (метод локтя): {optimal_clusters}")

            # Построение графика
            plt.figure(figsize=(12, 6))
            plt.plot(list(cluster_range), normalized_inertia, 'bo-')
            plt.axvline(x=optimal_clusters, color='r', linestyle='--')
            plt.title('Метод локтя для определения оптимального числа кластеров')
            plt.xlabel('Количество кластеров')
            plt.ylabel('Нормализованная инерция')
            plt.grid(True)

            if save_plot_path:
                os.makedirs(os.path.dirname(save_plot_path), exist_ok=True)
                plt.savefig(save_plot_path)
                print(f"График сохранен в {save_plot_path}")

            plt.close()

            return optimal_clusters

        elif method == 'silhouette':
            silhouette_scores = []

            for n_clusters in cluster_range:
                if n_clusters <= self.user_profiles_scaled.shape[0] - 1:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    cluster_labels = kmeans.fit_predict(self.user_profiles_scaled)
                    silhouette_avg = silhouette_score(self.user_profiles_scaled, cluster_labels)
                    silhouette_scores.append(silhouette_avg)
                    print(f"Кластеров: {n_clusters}, Коэффициент силуэта: {silhouette_avg:.4f}")

            optimal_index = np.argmax(silhouette_scores)
            optimal_clusters = list(cluster_range)[optimal_index]

            print(f"Оптимальное количество кластеров (метод силуэта): {optimal_clusters}")

            plt.figure(figsize=(12, 6))
            plt.plot(list(cluster_range)[:len(silhouette_scores)], silhouette_scores, 'bo-')
            plt.axvline(x=optimal_clusters, color='r', linestyle='--')
            plt.title('Метод силуэта для определения оптимального числа кластеров')
            plt.xlabel('Количество кластеров')
            plt.ylabel('Средний коэффициент силуэта')
            plt.grid(True)

            if save_plot_path:
                os.makedirs(os.path.dirname(save_plot_path), exist_ok=True)
                plt.savefig(save_plot_path)
                print(f"График сохранен в {save_plot_path}")

            plt.close()

            return optimal_clusters

        else:
            raise ValueError("Метод должен быть 'elbow' или 'silhouette'")

    def perform_clustering(self, n_clusters=None, save_model_path=None):
        if n_clusters is None:
            if self.n_clusters is None:
                self.n_clusters = self.find_optimal_clusters(max_clusters=200)
            n_clusters = self.n_clusters
        else:
            self.n_clusters = n_clusters

        print(f"Выполнение кластеризации с {n_clusters} кластерами...")

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(self.user_profiles_scaled)

        self.kmeans_model = kmeans

        self.user_clusters = pd.DataFrame(
            {'cluster': cluster_labels},
            index=self.user_profiles_scaled.index
        )

        cluster_counts = self.user_clusters['cluster'].value_counts().sort_index()
        print("Распределение пользователей по кластерам:")
        for cluster_id, count in cluster_counts.items():
            print(f"Кластер {cluster_id}: {count} пользователей")

        if save_model_path:
            try:

                save_dir = os.path.dirname(save_model_path)
                if save_dir and not os.path.exists(save_dir):
                    os.makedirs(save_dir, exist_ok=True)
                    print(f"Создана директория: {save_dir}")

                clustering_data = {
                    'kmeans_model': self.kmeans_model,
                    'n_clusters': self.n_clusters,
                    'user_clusters': self.user_clusters
                }

                joblib.dump(clustering_data, save_model_path)

                if os.path.exists(save_model_path):
                    print(f"Модель кластеризации успешно сохранена в {save_model_path}")
                    print(f"Размер файла: {os.path.getsize(save_model_path)} байт")
                else:
                    print(f"Ошибка: файл {save_model_path} не был создан")
            except Exception as e:
                print(f"Ошибка при сохранении модели кластеризации: {e}")
                import traceback
                print(traceback.format_exc())

            return self.user_clusters

    def build_knn_model(self, n_neighbors=5, save_model_path=None):

        print(f"Построение модели KNN с {n_neighbors} соседями...")

        knn = NearestNeighbors(n_neighbors=n_neighbors, algorithm='auto', metric='euclidean')
        knn.fit(self.user_profiles_scaled)
        self.knn_model = knn

        if save_model_path:
            try:
                save_dir = os.path.dirname(save_model_path)
                if save_dir and not os.path.exists(save_dir):
                    os.makedirs(save_dir, exist_ok=True)
                    print(f"Создана директория: {save_dir}")

                knn_data = {
                    'knn_model': self.knn_model,
                    'n_neighbors': n_neighbors
                }

                joblib.dump(knn_data, save_model_path)
                if os.path.exists(save_model_path):
                    print(f"Модель KNN успешно сохранена в {save_model_path}")
                    print(f"Размер файла: {os.path.getsize(save_model_path)} байт")
                else:
                    print(f"Ошибка: файл {save_model_path} не был создан")
            except Exception as e:
                print(f"Ошибка при сохранении модели KNN: {e}")
                import traceback
                print(traceback.format_exc())

            return self.knn_model

    def find_similar_users(self, user_profile, n_neighbors=5):
        if self.knn_model is None:
            self.build_knn_model(n_neighbors=n_neighbors)

        if isinstance(user_profile, dict):
            user_profile_df = pd.DataFrame([user_profile])
        else:
            user_profile_df = user_profile
        if self.scaler is not None:
            user_profile_scaled = self.scaler.transform(user_profile_df)
        else:
            user_profile_scaled = user_profile_df.values

        distances, indices = self.knn_model.kneighbors(user_profile_scaled)

        return distances[0], [self.user_profiles_scaled.index[idx] for idx in indices[0]]


if __name__ == "__main__":
    try:
        if not os.path.exists('models'):
            os.makedirs('models')
            print("Создана директория 'models'")

        profiles_path = 'models/user_profiles.pkl'
        if os.path.exists(profiles_path):
            clustering = UserClustering(profiles_path=profiles_path)
            print("Профили пользователей успешно загружены")
        else:
            print(f"Файл профилей {profiles_path} не найден. Сначала запустите data_processing.py")
            exit(1)

        optimal_clusters = clustering.find_optimal_clusters(
            max_clusters=200,
            method='elbow',
            save_plot_path='models/elbow_plot.png'
        )

        user_clusters = clustering.perform_clustering(
            n_clusters=optimal_clusters,
            save_model_path='models/kmeans_model.pkl'
        )

        knn_model = clustering.build_knn_model(
            n_neighbors=5,
            save_model_path='models/knn_model.pkl'
        )

        print("Кластеризация и построение модели KNN завершены!")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
