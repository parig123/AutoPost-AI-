// API Wrapper
const API = {
    async request(endpoint, options = {}) {
        const defaultHeaders = {
            'Content-Type': 'application/json'
        };

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(`/api${endpoint}`, config);
            
            if (response.status === 401) {
                // Return null or handle as needed without forced redirect
                return null;
            }
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'API Request Failed');
            }
            
            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            if (typeof showToast === 'function') {
                showToast(error.message, 'error');
            }
            throw error;
        }
    },

    // Auth API Calls
    async getCurrentUser() {
        return this.request('/auth/me', { method: 'GET' });
    },

    async getAccounts() {
        return this.request('/auth/accounts', { method: 'GET' });
    },

    async switchAccount(accountId) {
        return this.request(`/auth/switch/${accountId}`, { method: 'POST' });
    },

    async logout() {
        return this.request('/auth/logout', { method: 'POST' });
    },

    async initiateLinkedInLogin() {
        return this.request('/auth/linkedin', { method: 'GET' });
    },

    // Specific API Calls
    async generateContent(topic, tone, length, imageStyle) {
        return this.request('/posts/generate', {
            method: 'POST',
            body: JSON.stringify({ topic, tone, length, imageStyle })
        });
    },

    async updatePost(id, data) {
        return this.request(`/posts/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deletePost(id) {
        return this.request(`/posts/${id}`, {
            method: 'DELETE'
        });
    },

    async createPost(data) {
        return this.request('/posts', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async publishPost(id) {
        return this.request(`/posts/${id}/publish`, {
            method: 'POST'
        });
    },

    // Analytics API Calls
    async getStats() {
        return this.request('/analytics', { method: 'GET' });
    },

    async getRecentActivity() {
        return this.request('/analytics/activity', { method: 'GET' });
    }
};

// Global Auth State Manager
const Auth = {
    user: null,
    accounts: [],
    activeAccountId: null,
    
    async init() {
        try {
            const data = await API.getCurrentUser();
            if (data) {
                this.user = data;
                await this.refreshAccounts();
            } else {
                this.user = null;
            }
            this.updateUI();
        } catch (error) {
            this.user = null;
            this.updateUI();
        }
    },

    async refreshAccounts() {
        try {
            const data = await API.getAccounts();
            this.accounts = data.accounts;
            this.activeAccountId = data.active_account_id;
        } catch (error) {
            console.error('Failed to fetch accounts:', error);
        }
    },
    
    updateUI() {
        const authSection = document.getElementById('authSection');
        if (!authSection) return;
        
        if (this.user && this.user.active_account) {
            const account = this.user.active_account;
            authSection.innerHTML = `
                <div class="flex items-center gap-4">
                    <!-- Account Switcher Dropdown -->
                    <div class="relative" id="accountSwitcherContainer">
                        <button id="accountSwitcherBtn" class="flex items-center gap-1.5 p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all">
                            <img src="${account.profile_picture_url || 'https://ui-avatars.com/api/?name=' + account.name}" alt="Profile" class="w-7 h-7 rounded-full">
                            <i class="fa-solid fa-chevron-down text-[10px] opacity-50 ml-1"></i>
                        </button>
                        
                        <div id="accountDropdown" class="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-100 dark:border-slate-800 hidden z-50 overflow-hidden">
                            <div class="p-2 max-h-64 overflow-y-auto" id="accountList">
                                <!-- Accounts populated by JS -->
                            </div>
                            <div class="border-t border-slate-100 dark:border-slate-800 p-2">
                                <button id="addAccountBtn" class="w-full text-left px-3 py-2 text-xs font-medium text-primary hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg flex items-center gap-2">
                                    <i class="fa-solid fa-plus"></i>
                                    Add LinkedIn Account
                                </button>
                                <button id="logoutBtn" class="w-full text-left px-3 py-2 text-xs font-medium text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg flex items-center gap-2 mt-1">
                                    <i class="fa-solid fa-right-from-bracket"></i>
                                    Logout
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Add interaction logic
            this.setupAccountSwitcher();
        } else {
            authSection.innerHTML = `
                <a href="/login" class="px-4 py-2 bg-primary text-white font-medium rounded-lg hover:bg-blue-700 transition-colors text-sm">Login</a>
            `;
        }
    },

    setupAccountSwitcher() {
        const btn = document.getElementById('accountSwitcherBtn');
        const dropdown = document.getElementById('accountDropdown');
        const list = document.getElementById('accountList');
        
        if (!btn || !dropdown) return;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('hidden');
            this.renderAccountList();
        });

        document.addEventListener('click', () => dropdown.classList.add('hidden'));

        document.getElementById('addAccountBtn')?.addEventListener('click', async () => {
            try {
                const data = await API.initiateLinkedInLogin();
                if (data.auth_url) window.location.href = data.auth_url;
            } catch (error) {
                console.error('Failed to initiate LinkedIn login:', error);
            }
        });

        document.getElementById('logoutBtn')?.addEventListener('click', async () => {
            try {
                await API.logout();
                window.location.href = '/';
            } catch (error) {
                console.error('Logout failed:', error);
            }
        });
    },

    renderAccountList() {
        const list = document.getElementById('accountList');
        if (!list) return;

        list.innerHTML = this.accounts.map(acc => {
            const isOrg = acc.account_type === 'ORGANIZATION';
            const icon = isOrg ? 'fa-building' : 'fa-user';
            const typeLabel = isOrg ? 'Company' : 'Personal';
            
            return `
                <button class="account-item w-full text-left px-3 py-2 rounded-lg flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${acc.id === this.activeAccountId ? 'bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700' : ''}" data-id="${acc.id}">
                    <div class="relative">
                        <img src="${acc.profile_picture_url || 'https://ui-avatars.com/api/?name=' + acc.name}" class="w-8 h-8 rounded-full">
                        <div class="absolute -bottom-1 -right-1 w-4 h-4 bg-white dark:bg-slate-800 rounded-full flex items-center justify-center border border-slate-100 dark:border-slate-700">
                            <i class="fa-solid ${icon} text-[8px] text-primary"></i>
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-xs font-semibold truncate">${acc.name}</p>
                        <p class="text-[10px] text-slate-500 truncate">${typeLabel} • ${acc.id === this.activeAccountId ? 'Active' : 'Switch'}</p>
                    </div>
                    ${acc.id === this.activeAccountId ? '<i class="fa-solid fa-check text-primary text-[10px]"></i>' : ''}
                </button>
            `;
        }).join('');

        // Add click events to switch accounts
        list.querySelectorAll('.account-item').forEach(item => {
            item.addEventListener('click', async () => {
                const id = parseInt(item.dataset.id);
                if (id === this.activeAccountId) return;
                
                try {
                    await API.switchAccount(id);
                    window.location.reload();
                } catch (error) {
                    console.error('Failed to switch account:', error);
                }
            });
        });
    }
};

// Initialize auth state on page load
document.addEventListener('DOMContentLoaded', () => {
    Auth.init();
});
