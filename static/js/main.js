// Simple interactivity
document.addEventListener('DOMContentLoaded', function() {
    // Add click tracking for external links
    document.querySelectorAll('a[href^="http"]').forEach(link => {
        if (!link.href.includes(window.location.hostname)) {
            link.addEventListener('click', function() {
                console.log('External link clicked:', this.href);
            });
        }
    });
});
