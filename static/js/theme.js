(function () {
    const body = document.body;
    const toggleBtn = document.getElementById("themeToggle");
    const icon = document.getElementById("themeIcon");

    function setTheme(theme) {
        if (theme === "dark") {
            body.classList.add("dark-mode");
            icon.textContent = "🌙";
        } else {
            body.classList.remove("dark-mode");
            icon.textContent = "☀️";
        }
        localStorage.setItem("theme", theme);
    }

    // Load saved theme
    const savedTheme = localStorage.getItem("theme") || "light";
    setTheme(savedTheme);

    // Toggle
    toggleBtn.addEventListener("click", () => {
        const currentTheme = body.classList.contains("dark-mode") ? "dark" : "light";
        setTheme(currentTheme === "dark" ? "light" : "dark");
    });
})();



document.addEventListener("DOMContentLoaded", function () {

    /* ===============================
       DELETE BUTTON ENABLE/DISABLE
    ================================ */

    const passwordInput = document.getElementById("deletePassword");
    const confirmCheckbox = document.getElementById("confirmDelete");
    const deleteBtn = document.getElementById("deleteBtn");

    function updateDeleteButtonState() {
        if (!passwordInput || !confirmCheckbox || !deleteBtn) return;

        const passwordFilled = passwordInput.value.trim().length > 0;
        const checkboxChecked = confirmCheckbox.checked;

        deleteBtn.disabled = !(passwordFilled && checkboxChecked);
    }

    if (passwordInput && confirmCheckbox && deleteBtn) {
        passwordInput.addEventListener("input", updateDeleteButtonState);
        confirmCheckbox.addEventListener("change", updateDeleteButtonState);
    }

    /* ===============================
       AUTO-SHOW TOASTS
    ================================ */

    document.querySelectorAll('.toast').forEach(function (toastEl) {
        new bootstrap.Toast(toastEl, { delay: 4000 }).show();
    });

    /* ===============================
       REOPEN DELETE MODAL IF ERROR
    ================================ */

    const deleteError = "{{ delete_error|default('') }}";

    if (deleteError === "True") {
        const modalEl = document.getElementById("deleteAccountModal");
        if (modalEl) {
            new bootstrap.Modal(modalEl).show();
        }
    }

});
