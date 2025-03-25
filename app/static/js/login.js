document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    
    // 检查是否已登录，如果已登录，则跳转到首页
    checkAuthStatus();
    
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            showError('用户名和密码不能为空');
            return;
        }
        
        // 禁用提交按钮并显示加载状态
        const submitButton = document.querySelector('#login-form button[type="submit"]');
        const originalButtonText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = '登录中...';
        
        // 清除之前的错误提示
        loginError.classList.add('d-none');
        
        // 发送登录请求
        fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                password: password
            }),
            credentials: 'include'  // 包含凭证，接收cookie
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 保存token到localStorage（备用，cookie已由服务器设置）
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('user_info', JSON.stringify(data.user));
                
                // 显示成功消息
                showToast('登录成功', 'success');
                
                // 跳转到首页
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                showError(data.message || '登录失败，请检查用户名和密码');
                
                // 恢复提交按钮
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }
        })
        .catch(error => {
            console.error('登录请求错误:', error);
            showError('网络错误，请稍后重试');
            
            // 恢复提交按钮
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
        });
    });
    
    // 显示错误信息
    function showError(message) {
        loginError.textContent = message;
        loginError.classList.remove('d-none');
    }
    
    // 显示toast消息
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        
        bsToast.show();
        
        // 自动清理DOM
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
    
    // 检查认证状态
    function checkAuthStatus() {
        // 检查cookie
        const cookieToken = getCookie('access_token');
        
        // 检查localStorage
        const localToken = localStorage.getItem('access_token');
        
        // 使用cookie或localStorage中的token
        const token = cookieToken || localToken;
        
        if (token) {
            fetch('/api/auth/check-auth', {
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                credentials: 'include'  // 包含凭证
            })
            .then(response => response.json())
            .then(data => {
                if (data.authenticated) {
                    // 已登录，跳转到首页
                    window.location.href = '/';
                } else {
                    // 清除失效的token
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('user_info');
                    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                }
            })
            .catch(error => {
                console.error('检查认证状态错误:', error);
                // 发生错误时清除token
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            });
        }
    }
    
    // 获取cookie的辅助函数
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
}); 