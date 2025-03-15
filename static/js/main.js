document.addEventListener('DOMContentLoaded', function() {
    // Handle article generation
    document.querySelectorAll('.generate-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const articleId = this.dataset.articleId;
            const statusCell = document.querySelector(`tr[data-article-id="${articleId}"] .status-cell`);
            
            try {
                button.disabled = true;
                statusCell.textContent = 'processing';
                
                const response = await fetch(`/generate/${articleId}`, {
                    method: 'POST'
                });
                
                if (!response.ok) {
                    throw new Error('Generation failed');
                }
                
                const result = await response.json();
                statusCell.textContent = 'completed';
                
                // Refresh the page to show the new content
                location.reload();
            } catch (error) {
                statusCell.textContent = 'failed';
                button.disabled = false;
                alert('Failed to generate article: ' + error.message);
            }
        });
    });

    // Handle article view modal
    document.querySelectorAll('.view-btn').forEach(button => {
        button.addEventListener('click', function() {
            const content = this.dataset.articleContent;
            document.getElementById('articleContent').innerHTML = content.replace(/\n/g, '<br>');
        });
    });

    // Handle API key forms
    document.querySelectorAll('.api-key-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            try {
                const response = await fetch('/api/keys', {
                    method: 'POST',
                    body: new FormData(this)
                });
                
                if (!response.ok) {
                    throw new Error('Failed to update API key');
                }
                
                alert('API key updated successfully');
            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    });
});
