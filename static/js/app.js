// Global Application Logic

// Theme Toggle Logic
const themeToggleBtn = document.getElementById('themeToggle');
const htmlElement = document.documentElement;

// Check for saved theme preference or system preference
const savedTheme = localStorage.getItem('theme');
const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

if (savedTheme === 'dark' || (!savedTheme && systemDark)) {
    htmlElement.classList.add('dark');
}

themeToggleBtn?.addEventListener('click', () => {
    htmlElement.classList.toggle('dark');
    const isDark = htmlElement.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
});

// Toast Notification System
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    // Style based on type
    const bgClass = type === 'success' ? 'bg-emerald-500' : 
                    type === 'error' ? 'bg-rose-500' : 'bg-slate-800';
    
    const iconClass = type === 'success' ? 'fa-check-circle' : 
                      type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';

    toast.className = `${bgClass} text-white px-6 py-4 rounded-xl shadow-lg flex items-center gap-3 toast-enter max-w-md`;
    
    toast.innerHTML = `
        <i class="fa-solid ${iconClass} text-xl"></i>
        <div class="flex-1">
            <p class="font-medium text-sm">${message}</p>
        </div>
        <button class="opacity-70 hover:opacity-100 transition-opacity" onclick="this.parentElement.remove()">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
