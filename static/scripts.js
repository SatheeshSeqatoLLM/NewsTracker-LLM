document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const countryList = document.getElementById('country-list');

    const countries = {
        "us": "United States", "gb": "United Kingdom", "ca": "Canada", "au": "Australia", "in": "India",
        "de": "Germany", "fr": "France", "jp": "Japan", "cn": "China", "ru": "Russia", "br": "Brazil"
    };

    function populateCountryList() {
        for (const code in countries) {
            const item = document.createElement('li');
            item.textContent = countries[code];
            item.dataset.code = code;
            countryList.appendChild(item);
        }
    }

    countryList.addEventListener('click', function(event) {
        if (event.target.tagName === 'LI') {
            const countryCode = event.target.dataset.code;
            fetchNews('', countryCode);
        }
    });

    function fetchNews(topic = '', country = '') {
        let url = '/news';
        const params = new URLSearchParams();
        if (topic) params.append('topic', topic);
        if (country) params.append('country', country);

        if (params.toString()) {
            url += `?${params.toString()}`;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data) {
                    clearNews();
                    populateTicker(data.trending);
                    populateFeatured(data.featured);
                    populateRelated(data.related);
                    populateHighlights(data.highlights);
                }
            })
            .catch(error => console.error('Error fetching or processing news:', error));
    }

    searchForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const topic = searchInput.value.trim();
        fetchNews(topic, ''); // Clear country selection on new search
    });

    function clearNews() {
        document.querySelector('.ticker').innerHTML = '';
        document.querySelector('.featured-news').innerHTML = '';
        document.querySelector('.related-articles').innerHTML = '';
        document.querySelector('.side-highlights').innerHTML = '';
    }

    function populateTicker(articles) {
        if (!articles || articles.length === 0) return;
        const ticker = document.querySelector('.ticker');
        articles.forEach(article => {
            const item = document.createElement('div');
            item.classList.add('ticker__item');
            item.innerHTML = `<a href="${article.url}" target="_blank">${article.title}</a>`;
            ticker.appendChild(item);
        });
    }

    function populateFeatured(article) {
        const featured = document.querySelector('.featured-news');
        if (article) {
            let imageHtml = '';
            if (article.image_url) {
                imageHtml = `<img src="${article.image_url}" alt="${article.title}">`;
            }
            featured.innerHTML = `
                <h2>${article.title}</h2>
                ${imageHtml}
                <p>${article.summary}</p>
                <a href="${article.url}" target="_blank">Read more</a>
            `;
        }
    }

    function populateRelated(articles) {
        if (!articles || articles.length === 0) return;
        const related = document.querySelector('.related-articles');
        articles.forEach(article => {
            const item = document.createElement('div');
            item.classList.add('news-item'); // Add a class for styling
            let imageHtml = '';
            if (article.image_url) {
                imageHtml = `<img src="${article.image_url}" alt="${article.title}">`;
            }
            item.innerHTML = `
                <h4><a href="${article.url}" target="_blank">${article.title}</a></h4>
                ${imageHtml}
                <p>${article.summary}</p>
            `;
            related.appendChild(item);
        });
    }

    function populateHighlights(articles) {
        if (!articles || articles.length === 0) return;
        const highlights = document.querySelector('.side-highlights');
        articles.forEach(article => {
            const item = document.createElement('div');
            item.classList.add('news-item'); // Add a class for styling
            let imageHtml = '';
            if (article.image_url) {
                imageHtml = `<img src="${article.image_url}" alt="${article.title}" style="width: 100%; height: auto;">`;
            }
            item.innerHTML = `
                <h5><a href="${article.url}" target="_blank">${article.title}</a></h5>
                ${imageHtml}
            `;
            highlights.appendChild(item);
        });
    }

    // Initial setup
    populateCountryList();
    fetchNews(); // Initial fetch for general news
});