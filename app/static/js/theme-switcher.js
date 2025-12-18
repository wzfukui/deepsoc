// DeepSOC Theme Switcher - Universal
// 可在所有页面使用的主题切换功能

(function() {
    'use strict';
    
    // 主题配置
    const THEME_KEY = 'deepsoc_theme';
    const DEFAULT_THEME = 'dark';
    
    // 加载并应用主题
    function loadTheme() {
        const savedTheme = localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
        applyTheme(savedTheme);
        return savedTheme;
    }
    
    // 应用主题
    function applyTheme(theme) {
        const body = document.body;
        const html = document.documentElement;
        
        // 移除所有主题类
        body.classList.remove('light-theme', 'dark-theme');
        html.classList.remove('light-theme');
        
        // 应用新主题
        if (theme === 'light') {
            body.classList.add('light-theme');
            html.classList.add('light-theme');
        } else {
            body.classList.add('dark-theme');
        }
        
        console.log(`%c[主题] 已应用${theme === 'light' ? '浅色' : '深色'}主题`, 'color: #4CAF50;');
    }
    
    // 切换主题
    function toggleTheme() {
        const currentTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        applyTheme(newTheme);
        localStorage.setItem(THEME_KEY, newTheme);
        
        // 触发自定义事件，通知其他组件主题已改变
        const event = new CustomEvent('themeChanged', { detail: { theme: newTheme } });
        document.dispatchEvent(event);
        
        console.log(`%c[主题] 切换到${newTheme === 'light' ? '浅色' : '深色'}主题`, 'color: #4CAF50;');
        
        return newTheme;
    }
    
    // 获取当前主题
    function getCurrentTheme() {
        return document.body.classList.contains('light-theme') ? 'light' : 'dark';
    }
    
    // 初始化主题切换器按钮
    function initThemeSwitcher() {
        // 查找所有主题切换按钮
        const switchers = document.querySelectorAll('[data-theme-switcher]');
        
        switchers.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const newTheme = toggleTheme();
                
                // 显示Toast通知（如果存在showToast函数）
                if (typeof window.showToast === 'function') {
                    window.showToast(`已切换到${newTheme === 'light' ? '浅色' : '深色'}主题`, 'success');
                }
            });
        });
        
        // 兼容旧的ID方式
        const themeSwitcherById = document.getElementById('theme-switcher');
        if (themeSwitcherById && !themeSwitcherById.hasAttribute('data-theme-switcher')) {
            themeSwitcherById.addEventListener('click', (e) => {
                e.preventDefault();
                const newTheme = toggleTheme();
                
                if (typeof window.showToast === 'function') {
                    window.showToast(`已切换到${newTheme === 'light' ? '浅色' : '深色'}主题`, 'success');
                }
            });
        }
        
        console.log(`%c[主题] 已初始化 ${switchers.length + (themeSwitcherById ? 1 : 0)} 个主题切换器`, 'color: #4CAF50;');
    }
    
    // 页面加载时自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            loadTheme();
            initThemeSwitcher();
        });
    } else {
        loadTheme();
        initThemeSwitcher();
    }
    
    // 暴露API到全局
    window.DeepSOCTheme = {
        load: loadTheme,
        apply: applyTheme,
        toggle: toggleTheme,
        getCurrent: getCurrentTheme,
        init: initThemeSwitcher
    };
    
    // 兼容性：保留旧的全局函数
    window.loadTheme = loadTheme;
    window.toggleTheme = toggleTheme;
    window.applyTheme = applyTheme;
    
})();
