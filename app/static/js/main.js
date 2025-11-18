// app/static/js/main.js

document.addEventListener('DOMContentLoaded', function () {

    console.log("Farma Vida App: main.js cargado y listo.");

    // --- FUNCIONALIDAD 1: Tooltips (SE QUEDA IGUAL) ---
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // --- FUNCIONALIDAD 2: Confirmación de Logout (SE QUEDA IGUAL) ---
    const logoutButtons = document.querySelectorAll('a[href*="/logout"]');
    logoutButtons.forEach(function(button) {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            const userConfirmed = confirm('¿Estás seguro de que quieres cerrar la sesión?');
            if (userConfirmed) {
                window.location.href = this.href;
            }
        });
    });


    // ===================================================================
    // === CÓDIGO AÑADIDO (NO REEMPLAZA NADA) ===
    // ===================================================================
    // --- Lógica para el Menú Móvil ---
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');

    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', function(event) {
            event.stopPropagation();
            sidebar.classList.toggle('is-open');
        });
    }
    
    if (mainContent && sidebar) {
        mainContent.addEventListener('click', function() {
            if (sidebar.classList.contains('is-open')) {
                sidebar.classList.remove('is-open');
            }
        });
    }

}); // <-- El nuevo código va antes de esta línea de cierre