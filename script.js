document.querySelector('.mobile-toggle').addEventListener('click', function() {
    const nav = document.querySelector('.nav-links');
    nav.style.display = nav.style.display === 'flex' ? 'none' : 'flex';
    nav.style.flexDirection = 'column';
    nav.style.position = 'absolute';
    nav.style.top = '70px';
    nav.style.right = '24px';
    nav.style.background = '#fff';
    nav.style.padding = '24px';
    nav.style.borderRadius = '12px';
    nav.style.boxShadow = '0 10px 40px rgba(0,0,0,0.1)';
});

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

document.getElementById('contactForm').addEventListener('submit', function(e) {
    e.preventDefault();
    alert('Thank you! We\'ll be in touch within 24 hours to schedule your free automation audit.');
    this.reset();
});
