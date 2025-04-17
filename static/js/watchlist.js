document.addEventListener('DOMContentLoaded', function () {
    // Handle "Remove" button clicks
    document.querySelectorAll('.remove-btn').forEach(button => {
        button.addEventListener('click', async function() {
            try {
                const movieId = this.getAttribute('data-movie-id');
                if (!movieId) {
                    console.error('No movie ID found');
                    return;
                }

                if (confirm('Are you sure you want to remove this movie from your watchlist?')) {
                    const response = await fetch(`/api/watchlist/remove/${movieId}`, {
                        method: 'DELETE'
                    });

                    if (response.ok) {
                        const card = this.closest('.movie-card');
                        card.style.opacity = '0';
                        card.style.transition = 'opacity 0.3s ease';
                        
                        setTimeout(() => {
                            card.remove();
                            checkEmptyWatchlist();
                        }, 300);
                    } else {
                        const data = await response.json();
                        alert(data.error || 'Failed to remove movie from watchlist');
                    }
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to remove movie from watchlist');
            }
        });
    });

    function checkEmptyWatchlist() {
        const movieGrid = document.querySelector('.movie-grid');
        if (!movieGrid.querySelector('.movie-card')) {
            movieGrid.innerHTML = `
                <div class="empty-watchlist">
                    <p>Your watchlist is empty. Start adding movies!</p>
                    <a href="/" class="browse-movies-btn">Browse Movies</a>
                </div>
            `;
        }
    }

    // Handle "Mark as Watched" button clicks
    const watchButtons = document.querySelectorAll('.watch-btn');
    if (watchButtons) {
        watchButtons.forEach(button => {
            button.addEventListener('click', function () {
                const card = this.closest('.movie-card');
                if (card) {
                    card.classList.toggle('watched');
                    const isWatched = card.classList.contains('watched');
                    showNotification(
                        isWatched ? 'Marked as watched' : 'Marked as unwatched',
                        'success'
                    );
                }
            });
        });
    }

    // Handle filter changes
    const filterSelect = document.querySelector('.watchlist-filter select');
    if (filterSelect) {
        filterSelect.addEventListener('change', function () {
            const filter = this.value;
            const cards = document.querySelectorAll('.movie-card');

            cards.forEach(card => {
                switch (filter) {
                    case 'watched':
                        card.style.display = card.classList.contains('watched') ? 'block' : 'none';
                        break;
                    case 'unwatched':
                        card.style.display = !card.classList.contains('watched') ? 'block' : 'none';
                        break;
                    default:
                        card.style.display = 'block';
                }
            });
        });
    }
});

// Notification helper function (defined outside the DOMContentLoaded event)
function showNotification(message, type) {
    // Remove any existing notifications first
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());

    // Create and add new notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
