async function addToWatchlist(button, movieId) {
    try {
        button.disabled = true;
        
        const response = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ movie_id: parseInt(movieId) })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            button.innerHTML = '<i class="fas fa-check"></i> Added';
            button.classList.add('added');
            showNotification('Movie added to watchlist!', 'success');
        } else {
            button.disabled = false;
            showNotification(data.error || 'Failed to add to watchlist', 'error');
        }
    } catch (error) {
        button.disabled = false;
        console.error('Error:', error);
        showNotification('Failed to add to watchlist', 'error');
    }
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function validateSearch(form) {
    const query = form.query.value.trim();
    if (!query) {
        showNotification('Please enter a search term', 'error');
        return false;
    }
    return true;
} 