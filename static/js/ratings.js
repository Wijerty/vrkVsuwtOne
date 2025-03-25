document.addEventListener('DOMContentLoaded', function() {
    console.log('Инициализация обработчика рейтингов');

    const isLoggedIn = document.body.dataset.loggedIn === 'true';
    console.log('Пользователь авторизован:', isLoggedIn);

    initAllRatingStars();

    updateSelectedMovies();

    document.getElementById('searchForm').addEventListener('submit', function(e) {
        e.preventDefault();
        searchMovies();
    });

    document.getElementById('recommendationForm').addEventListener('submit', function(e) {
        e.preventDefault();
        getRecommendations();
    });

    function initAllRatingStars() {
        document.querySelectorAll('.rating-container').forEach(function(container) {
            initRatingStars(container);
        });
    }

    function initRatingStars(container) {
        const stars = container.querySelectorAll('.star');
        const ratingInput = container.querySelector('.rating-value');
        const movieId = container.dataset.movieId;

        if (ratingInput.value) {
            updateStarsDisplay(stars, ratingInput.value);
        }

        stars.forEach(function(star) {
            star.addEventListener('mouseover', function() {
                const rating = this.dataset.rating;
                updateStarsDisplay(stars, rating);
            });

            container.addEventListener('mouseout', function() {
                const currentRating = ratingInput.value;
                updateStarsDisplay(stars, currentRating);
            });

            star.addEventListener('click', function(e) {
                e.preventDefault(); 
                const rating = this.dataset.rating;
                console.log(`Клик на звезду ${rating} для фильма ${movieId}`);

                ratingInput.value = rating;

                if (isLoggedIn) {
                    saveRating(movieId, rating);
                } else {
                    console.log('Пользователь не авторизован, оценка не будет сохранена');
                    alert('Войдите в систему, чтобы сохранять оценки');
                }

                updateSelectedMovies();
            });
        });
    }

    function updateStarsDisplay(stars, rating) {
        stars.forEach(function(s, index) {
            if (index < rating) {
                s.innerHTML = '★';
                s.classList.add('active');
            } else {
                s.innerHTML = '☆';
                s.classList.remove('active');
            }
        });
    }

    function saveRating(movieId, rating) {
        console.log(`Отправка запроса на сохранение оценки: фильм ${movieId}, оценка ${rating}`);

        fetch('/rate_movie', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                movie_id: movieId,
                rating: rating
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Ошибка сети при отправке оценки');
            }
            return response.json();
        })
        .then(data => {
            console.log('Ответ сервера при сохранении оценки:', data);
            if (data.success) {
                console.log('Оценка успешно сохранена');
            } else {
                console.error('Ошибка при сохранении оценки:', data.message);
                alert('Ошибка при сохранении оценки: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Ошибка при сохранении оценки:', error);
            alert('Произошла ошибка при сохранении оценки');
        });
    }

    function deleteRating(movieId) {
        console.log(`Удаление оценки для фильма ${movieId}`);

        if (!isLoggedIn) {
            console.log('Пользователь не авторизован, просто удаляем локально');
            const ratingInput = document.querySelector(`input[name="rating_${movieId}"]`);
            if (ratingInput) {
                ratingInput.value = '';
                const stars = ratingInput.closest('.rating-container').querySelectorAll('.star');
                updateStarsDisplay(stars, 0);
                updateSelectedMovies();
            }
            return;
        }

        const formData = new FormData();
        formData.append('movie_id', movieId);

        fetch('/delete_rating', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Ошибка сети при удалении оценки');
            }
            return response.json();
        })
        .then(data => {
            console.log('Ответ сервера при удалении оценки:', data);
            if (data.success) {
                console.log('Оценка успешно удалена');
                const ratingInput = document.querySelector(`input[name="rating_${movieId}"]`);
                if (ratingInput) {
                    ratingInput.value = '';
                    const stars = ratingInput.closest('.rating-container').querySelectorAll('.star');
                    updateStarsDisplay(stars, 0);
                }
                updateSelectedMovies();
            } else {
                console.error('Ошибка при удалении оценки:', data.message);
                alert('Ошибка при удалении оценки: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Ошибка при удалении оценки:', error);
            alert('Произошла ошибка при удалении оценки');
        });
    }

    function updateSelectedMovies() {
        console.log('Обновление списка оцененных фильмов');
        const ratedMoviesList = document.getElementById('ratedMoviesList');
        const noRatingsMessage = document.getElementById('noRatingsMessage');
        const getRecommendationsBtn = document.getElementById('getRecommendationsBtn');

        const ratedMovies = [];
        document.querySelectorAll('.rating-value').forEach(function(input) {
            if (input.value) {
                const movieId = input.name.split('_')[1];
                const movieCard = input.closest('.movie-card');
                const movieTitle = movieCard ? movieCard.querySelector('h5').textContent : `Фильм ${movieId}`;
                ratedMovies.push({
                    id: movieId,
                    title: movieTitle,
                    rating: input.value
                });
            }
        });

        console.log(`Найдено ${ratedMovies.length} оцененных фильмов`);

        if (ratedMovies.length > 0) {
            noRatingsMessage.style.display = 'none';
            ratedMoviesList.innerHTML = '';

            ratedMovies.forEach(function(movie) {
                const movieElement = document.createElement('div');
                movieElement.className = 'rated-movie';
                movieElement.innerHTML = `
                    <div class="rated-movie-title">${movie.title}</div>
                    <div class="rated-movie-rating">
                        Ваша оценка: ${movie.rating}
                        <span class="delete-rating" data-movie-id="${movie.id}">&times;</span>
                    </div>
                `;
                ratedMoviesList.appendChild(movieElement);

                movieElement.querySelector('.delete-rating').addEventListener('click', function() {
                    const movieId = this.dataset.movieId;
                    deleteRating(movieId);
                });
            });

            getRecommendationsBtn.disabled = false;
        } else {
            noRatingsMessage.style.display = 'block';
            ratedMoviesList.innerHTML = '';

            getRecommendationsBtn.disabled = true;
        }
    }

    function searchMovies() {
        const query = document.getElementById('searchQuery').value;
        const genre = document.getElementById('genreFilter').value;

        console.log(`Поиск фильмов: query="${query}", genre="${genre}"`);

        const formData = new FormData();
        formData.append('query', query);
        formData.append('genre', genre);

        fetch('/search_movies', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log(`Получено ${data.movies.length} результатов поиска`);

            const moviesList = document.getElementById('moviesList');
            const noMoviesMessage = document.getElementById('noMoviesMessage');

            if (data.movies && data.movies.length > 0) {
                moviesList.innerHTML = '';
                noMoviesMessage.style.display = 'none';

                data.movies.forEach(function(movie) {
    const movieElement = document.createElement('div');
    movieElement.className = 'col-md-6 mb-4';
    movieElement.innerHTML = `
        <div class="card movie-card">
            <div class="card-body">
                <h5 class="card-title">${movie.title}</h5>
                <p class="card-text">${movie.genres}</p>
                <div class="rating-container" data-movie-id="${movie.movieId}">
                    <div class="stars">
                        <span class="star" data-rating="1">☆</span>
                        <span class="star" data-rating="2">☆</span>
                        <span class="star" data-rating="3">☆</span>
                        <span class="star" data-rating="4">☆</span>
                        <span class="star" data-rating="5">☆</span>
                    </div>
                    <input type="hidden" name="rating_${movie.movieId}" class="rating-value" value="${movie.user_rating || ''}">
                </div>
            </div>
        </div>
    `;
    moviesList.appendChild(movieElement);

    initRatingStars(movieElement.querySelector('.rating-container'));
});
} else {
    moviesList.innerHTML = '';
    noMoviesMessage.style.display = 'block';
}
})
.catch(error => {
    console.error('Ошибка при поиске фильмов:', error);
    alert('Произошла ошибка при поиске фильмов');
});
}

function getRecommendations() {
    console.log("Запрос рекомендаций");

    document.getElementById('loading').style.display = 'block';
    document.getElementById('recommendationsContainer').style.display = 'block';

    const formData = new FormData();
    let hasRatings = false;

    document.querySelectorAll('.rating-value').forEach(function(input) {
        if (input.value) {
            formData.append(input.name, input.value);
            hasRatings = true;
        }
    });

    if (!hasRatings) {
        alert("Пожалуйста, оцените хотя бы один фильм");
        document.getElementById('loading').style.display = 'none';
        return;
    }

    fetch('/get_recommendations', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('loading').style.display = 'none';

        if (data.success) {
            const recommendationsList = document.getElementById('recommendationsList');
            recommendationsList.innerHTML = '';

            if (data.recommendations && data.recommendations.length > 0) {
                data.recommendations.forEach(function(movie) {
                    const movieElement = document.createElement('div');
                    movieElement.className = 'recommendation-card p-3 mb-3';

                    const score = parseFloat(movie.score);
                    const scorePercentage = Math.round((score / 5) * 100);

                    movieElement.innerHTML = `
                        <div class="recommendation-title">${movie.title}</div>
                        <div class="recommendation-score">
                            Рейтинг: ${score.toFixed(1)} / 5
                            <div class="progress mt-1">
                                <div class="progress-bar bg-warning" role="progressbar"
                                     style="width: ${scorePercentage}%"
                                     aria-valuenow="${score}" aria-valuemin="0" aria-valuemax="5">
                                </div>
                            </div>
                        </div>
                        <div class="recommendation-genres mt-2">${movie.genres}</div>
                    `;

                    recommendationsList.appendChild(movieElement);
                });
            } else {
                recommendationsList.innerHTML = '<div class="alert alert-info">Не удалось найти рекомендации на основе ваших оценок.</div>';
            }
        } else {
            document.getElementById('recommendationsList').innerHTML = `
                <div class="alert alert-danger">
                    Ошибка при получении рекомендаций: ${data.message || 'Неизвестная ошибка'}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Ошибка при получении рекомендаций:', error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('recommendationsList').innerHTML = `
            <div class="alert alert-danger">
                Произошла ошибка при получении рекомендаций. Пожалуйста, попробуйте позже.
            </div>
        `;
    });
}
});

