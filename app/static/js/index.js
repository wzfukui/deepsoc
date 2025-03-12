// DeepSOC 首页脚本

// API基础URL
const API_BASE_URL = '/api';

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    // 获取事件列表
    fetchEvents();
    
    // 刷新按钮点击事件
    document.getElementById('refresh-events').addEventListener('click', fetchEvents);
    
    // 表单提交事件
    document.getElementById('event-form').addEventListener('submit', (e) => {
        e.preventDefault();
        
        const eventData = {
            event_name: document.getElementById('event-name').value,
            message: document.getElementById('event-message').value,
            context: document.getElementById('event-context').value,
            severity: document.getElementById('event-severity').value,
            source: document.getElementById('event-source').value
        };
        
        createEvent(eventData);
    });
});

// 获取事件列表
async function fetchEvents() {
    try {
        const eventsContainer = document.getElementById('events-container');
        eventsContainer.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p class="mt-2">加载事件列表...</p>
            </div>
        `;
        
        const response = await fetch(`${API_BASE_URL}/event/list`);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayEvents(data.data);
        } else {
            showError('获取事件列表失败');
        }
    } catch (error) {
        console.error('获取事件列表出错:', error);
        showError('获取事件列表出错');
    }
}

// 显示事件列表
function displayEvents(events) {
    const container = document.getElementById('events-container');
    
    if (events.length === 0) {
        container.innerHTML = '<div class="text-center py-5"><p>暂无安全事件</p></div>';
        return;
    }
    
    let html = '';
    events.forEach(event => {
        const createdAt = new Date(event.created_at).toLocaleString();
        html += `
            <div class="card event-card severity-${event.severity} status-${event.status}" 
                 onclick="window.location.href='/warroom/${event.event_id}'">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <h5 class="card-title">${event.event_name}</h5>
                        <span class="badge bg-${getBadgeColor(event.status)}">${getStatusText(event.status)}</span>
                    </div>
                    <h6 class="card-subtitle mb-2 text-muted">ID: ${event.event_id} | 来源: ${event.source}</h6>
                    <p class="card-text">${event.message}</p>
                    <div class="d-flex justify-content-between">
                        <small class="text-muted">创建时间: ${createdAt}</small>
                        <span class="badge bg-${getSeverityColor(event.severity)}">${getSeverityText(event.severity)}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 创建安全事件
async function createEvent(eventData) {
    try {
        // 禁用提交按钮
        const submitButton = document.querySelector('#event-form button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            创建中...
        `;
        
        const response = await fetch(`${API_BASE_URL}/event/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(eventData)
        });
        
        const data = await response.json();
        
        // 恢复提交按钮
        submitButton.disabled = false;
        submitButton.innerHTML = '创建事件';
        
        if (data.status === 'success') {
            // 重置表单
            document.getElementById('event-form').reset();
            
            // 刷新事件列表
            fetchEvents();
            
            // 显示成功消息
            showSuccess('事件创建成功！');
            
            // 跳转到作战室
            setTimeout(() => {
                window.location.href = `/warroom/${data.data.event_id}`;
            }, 1000);
        } else {
            showError(data.message || '创建事件失败');
        }
    } catch (error) {
        console.error('创建事件出错:', error);
        showError('创建事件出错');
        
        // 恢复提交按钮
        const submitButton = document.querySelector('#event-form button[type="submit"]');
        submitButton.disabled = false;
        submitButton.innerHTML = '创建事件';
    }
}

// 显示成功消息
function showSuccess(message) {
    const toastContainer = document.getElementById('toast-container');
    const toastElement = document.createElement('div');
    toastElement.className = 'toast';
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    toastElement.innerHTML = `
        <div class="toast-header bg-success text-white">
            <strong class="me-auto">成功</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toastElement);
    
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // 自动移除
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// 显示错误消息
function showError(message) {
    const toastContainer = document.getElementById('toast-container');
    const toastElement = document.createElement('div');
    toastElement.className = 'toast';
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    toastElement.innerHTML = `
        <div class="toast-header bg-danger text-white">
            <strong class="me-auto">错误</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toastElement);
    
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // 自动移除
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// 获取状态对应的文本
function getStatusText(status) {
    const statusMap = {
        'pending': '待处理',
        'processing': '处理中',
        'round_finished': '轮次完成',
        'completed': '已完成',
        'resolved': '已解决',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

// 获取状态对应的徽章颜色
function getBadgeColor(status) {
    const colorMap = {
        'pending': 'secondary',
        'processing': 'primary', 
        'round_finished': 'info',
        'completed': 'success',
        'resolved': 'success',
        'failed': 'danger'
    };
    return colorMap[status] || 'secondary';
}

// 获取严重程度对应的文本
function getSeverityText(severity) {
    const severityMap = {
        'low': '低',
        'medium': '中',
        'high': '高'
    };
    return severityMap[severity] || severity;
}

// 获取严重程度对应的徽章颜色
function getSeverityColor(severity) {
    const colorMap = {
        'low': 'success',
        'medium': 'warning',
        'high': 'danger'
    };
    return colorMap[severity] || 'secondary';
} 