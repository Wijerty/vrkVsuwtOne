document.getElementById('recommendationForm').addEventListener('submit', function(e) {
    e.preventDefault();

    console.log("Начало обработки формы рекомендаций");

    document.getElementById('loading').style.display = 'block';
    document.getElementById('recommendationsContainer').style.display = 'none';

    const formData = new FormData();
    const userRatings = {};
    let hasRatings = false;

    document.querySelectorAll('.rating-value').forEach(function(input) {
        if (input.value) {
            const movieId = input.name.split('_')[1];
            formData.append(input.name, input.value);
            userRatings[movieId] = input.value;
            hasRatings = true;
            console.log(`Добавлена оценка: ${input.name} = ${input.value}`);
        }
    });

    if (!hasRatings) {
        console.log("Нет оценок для отправки!");
        alert("Пожалуйста, оцените хотя бы один фильм перед получением рекомендаций.");
        document.getElementById('loading').style.display = 'none';
        return;
    }

    console.log("Отправка данных на сервер:", JSON.stringify(userRatings));

    fetch('/get_recommendations', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log("Получен ответ от сервера");
        return response.json();
    })
    .then(data => {
        document.getElementById('loading').style.display = 'none';
        console.log("Обработка данных:", data);

        if (data.success) {
            const recommendationsList = document.getElementById('recommendationsList');
            recommendationsList.innerHTML = '';

            if (data.recommendations && data.recommendations.length > 0) {
                data.recommendations.forEach(function(movie, index) {
                    const movieElement = document.createElement('div');
                    movieElement.className = 'recommendation-card p-3 mb-3';

                    const score = parseFloat(movie.score);
                    const scorePercentage = Math.round((score / 5) * 100);
                    const starsHtml = '<div class="progress mb-2" style="height: 6px;"><div class="progress-bar bg-warning" role="progressbar" style="width: ' + scorePercentage + '%;" aria-valuenow="' + score + '" aria-valuemin="0" aria-valuemax="5"></div></div>';

                    movieElement.innerHTML = `
                        <div class="d-flex justify-content-between">
                            <h5 class="card-title">${index + 1}. ${movie.title}</h5>
                            <span class="badge bg-info">${movie.score.toFixed(1)}</span>
                        </div>
                        ${starsHtml}
                        <p class="card-text text-muted small">${movie.genres}</p>
                    `;
                    recommendationsList.appendChild(movieElement);
                });

                document.getElementById('recommendationsContainer').style.display = 'block';
            } else {
                recommendationsList.innerHTML = '<div class="alert alert-warning">Не удалось найти рекомендации на основе ваших оценок. Попробуйте оценить больше фильмов.</div>';
                document.getElementById('recommendationsContainer').style.display = 'block';
                console.log("Нет рекомендаций в ответе");
            }
        } else {
            alert(data.message || 'Произошла ошибка при получении рекомендаций.');
            console.log("Ошибка в ответе:", data.message);
        }
    })
    .catch(error => {
        document.getElementById('loading').style.display = 'none';
        console.error('Ошибка:', error);
        alert('Произошла ошибка при получении рекомендаций.');
    });
});