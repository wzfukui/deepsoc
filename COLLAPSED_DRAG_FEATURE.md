# 折叠状态拖动功能更新 (2025-12-18)

## 功能概述
添加了聊天框折叠状态（圆形按钮）下的拖动功能，同时保持点击展开的原有功能。

---

## 🎯 需求背景

**用户需求**: 
> 希望增加功能，支持作战室里悬浮按钮拖动。现在是输入框可拖动，但折叠收藏后变成导航按钮后，按钮不能拖动，希望同样增加支持。

**原有行为**:
- ✅ 展开状态：可以通过header拖动
- ❌ 折叠状态：只能点击展开，不能拖动

**期望行为**:
- ✅ 展开状态：可以通过header拖动
- ✅ 折叠状态：可以拖动移动位置 + 点击展开

---

## 💡 核心挑战

### 问题：如何区分点击和拖动？

折叠状态下的圆形按钮需要同时支持：
1. **点击** → 展开聊天框
2. **拖动** → 移动按钮位置

如果直接实现拖动，会导致点击操作失效！

### 解决方案：拖动阈值机制

引入 **`DRAG_THRESHOLD`** 常量，通过移动距离判断用户意图：

```javascript
const DRAG_THRESHOLD = 5; // 5像素阈值

// 计算移动距离
const deltaX = Math.abs(clientX - startX);
const deltaY = Math.abs(clientY - startY);
const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

if (distance > DRAG_THRESHOLD) {
    // 移动超过5px → 拖动
    hasMoved = true;
    executedrag();
} else {
    // 移动小于5px → 点击
    expandChatInput();
}
```

---

## 🔧 技术实现

### 1. 新增变量

```javascript
let hasMoved = false;      // 标记是否真正拖动过
let startX, startY;        // 记录鼠标/触摸开始位置
const DRAG_THRESHOLD = 5;  // 拖动阈值（像素）
```

### 2. 新增函数 `dragStartCollapsed`

专门处理折叠状态的拖动开始：

```javascript
function dragStartCollapsed(e) {
    // 只有折叠状态才处理
    if (!elements.chatInputFloat.classList.contains('collapsed')) {
        return;
    }
    
    // 记录开始位置
    if (e.type === 'touchstart') {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
    } else {
        startX = e.clientX;
        startY = e.clientY;
    }
    
    isDragging = true;
    hasMoved = false;
}
```

### 3. 改进 `drag` 函数

添加距离判断逻辑：

```javascript
function drag(e) {
    if (!isDragging) return;
    
    // 计算移动距离
    const distance = calculateDistance(startX, startY, clientX, clientY);
    
    // 超过阈值才标记为拖动
    if (distance > DRAG_THRESHOLD) {
        hasMoved = true;
        e.preventDefault();
        elements.chatInputFloat.classList.add('dragging');
    }
    
    if (!hasMoved) return; // 未超过阈值，不执行拖动
    
    // 执行拖动逻辑...
}
```

### 4. 改进 `dragEnd` 函数

根据 `hasMoved` 决定行为：

```javascript
function dragEnd(e) {
    if (!isDragging) return;
    
    // 折叠状态 + 未拖动 = 点击 → 展开
    if (elements.chatInputFloat.classList.contains('collapsed') && !hasMoved) {
        expandChatInput();
        return;
    }
    
    // 其他情况：正常结束拖动
    isDragging = false;
    hasMoved = false;
    elements.chatInputFloat.classList.remove('dragging');
}
```

### 5. 事件监听器调整

```javascript
// 展开状态：只在header区域监听
header.addEventListener('mousedown', dragStart);

// 折叠状态：整个元素都监听（圆形按钮）
elements.chatInputFloat.addEventListener('mousedown', dragStartCollapsed);
```

---

## 🎨 CSS样式优化

### 折叠状态样式

```css
.chat-input-float.collapsed {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    cursor: move;          /* 指示可拖动 */
    user-select: none;     /* 防止拖动时选中文本 */
    background: linear-gradient(135deg, var(--accent-blue), #0056b3);
}
```

### 拖动状态视觉反馈

```css
.chat-input-float.collapsed.dragging {
    cursor: grabbing;                          /* 抓取手势 */
    transform: translateX(-50%) scale(0.95);   /* 缩小5% */
    box-shadow: 0 8px 32px rgba(0, 112, 243, 0.8); /* 阴影增强 */
}
```

### Hover效果

```css
.chat-input-float.collapsed:hover {
    transform: translateX(-50%) scale(1.05);   /* 放大5% */
    box-shadow: 0 6px 24px rgba(0, 112, 243, 0.6);
}
```

---

## 📊 行为对比表

| 状态 | 操作 | 原行为 | 新行为 |
|------|------|--------|--------|
| 展开 | 点击Header | 无反应 | 无反应 |
| 展开 | 拖动Header | ✅ 拖动 | ✅ 拖动 |
| 折叠 | 点击按钮 | ✅ 展开 | ✅ 展开 |
| 折叠 | 拖动按钮 | ❌ 不支持 | ✅ 拖动（保持折叠） |
| 折叠 | 轻微移动(< 5px) | ✅ 展开 | ✅ 展开 |
| 折叠 | 明显拖动(> 5px) | ❌ 不支持 | ✅ 拖动 |

---

## 🎮 用户体验

### 交互流程

```
折叠状态的圆形按钮
    ↓
用户按下鼠标/触摸
    ↓
开始移动
    ↓
    ├─ 移动距离 < 5px ──→ 松开 ──→ 展开聊天框 ✅
    │
    └─ 移动距离 ≥ 5px ──→ 触发拖动
                           ↓
                       添加.dragging类
                           ↓
                       视觉反馈：缩小+阴影
                           ↓
                       跟随鼠标移动
                           ↓
                       松开 ──→ 停在新位置（保持折叠）✅
```

### 视觉反馈

1. **Hover状态** (未按下)
   - 按钮放大 5%
   - 阴影增强
   - Cursor: `move`

2. **拖动状态** (按下拖动中)
   - 按钮缩小 5%
   - 阴影进一步增强
   - Cursor: `grabbing`

3. **点击状态** (未拖动，松开)
   - 平滑展开动画
   - 聊天框完整显示

---

## 🐛 边界情况处理

### 1. 防止误触
- **5px阈值**: 防止轻微手抖误认为拖动
- **适合触摸屏**: 触摸操作精度较低，阈值合理

### 2. 防止文本选中
- `user-select: none` 防止拖动时选中页面文本

### 3. 视口边界限制
- 拖动时自动限制在可视区域内
- 不会拖出屏幕外

### 4. 状态冲突处理
```javascript
// 展开状态下，dragStartCollapsed直接return
if (!elements.chatInputFloat.classList.contains('collapsed')) {
    return;
}
```

---

## 📦 文件修改清单

```
修改文件: 2个
新增代码: +81行
删除代码: -18行
净增代码: +63行
```

### 详细修改:

1. **`app/static/js/warroom.js`** (+71行, -18行)
   - 新增 `dragStartCollapsed` 函数
   - 新增 `hasMoved`, `startX`, `startY` 变量
   - 新增 `DRAG_THRESHOLD` 常量
   - 改进 `drag` 函数（距离判断）
   - 改进 `dragEnd` 函数（点击/拖动区分）
   - 添加折叠元素的事件监听器

2. **`app/static/css/warroom.css`** (+10行)
   - 新增 `.collapsed` 的 `cursor: move`
   - 新增 `.collapsed` 的 `user-select: none`
   - 新增 `.collapsed.dragging` 样式
   - 移除非折叠状态的 `cursor: move`

---

## ✨ Git提交信息

**分支**: `ifirefox`  
**提交哈希**: `781ab77`

```
feat: 添加折叠状态下聊天框拖动功能

功能改进:
- 折叠状态下的圆形按钮现在可以拖动
- 使用拖动阈值(5px)区分点击和拖动
- 小于阈值视为点击,展开聊天框
- 大于阈值执行拖动,保持折叠状态

实现细节:
- dragStartCollapsed: 处理折叠状态拖动
- hasMoved标记: 区分拖动和点击
- DRAG_THRESHOLD: 5px阈值防误触
- 拖动时添加.dragging类

用户体验:
- 点击 → 展开
- 拖动 → 移动且保持折叠
- cursor: grabbing视觉反馈
- 平滑动画和缩放效果

统计: 2个文件修改, +81行, -18行
```

---

## 🧪 测试建议

### 基础功能测试

1. **展开状态**
   - ✅ Header区域可拖动
   - ✅ 拖动后位置保持
   - ✅ 边界限制正常

2. **折叠状态 - 拖动**
   - ✅ 按住圆形按钮拖动到新位置
   - ✅ 松开后停在新位置且保持折叠
   - ✅ 视觉反馈正常（缩小+阴影）

3. **折叠状态 - 点击**
   - ✅ 轻点圆形按钮立即展开
   - ✅ 轻微移动（< 5px）仍然展开
   - ✅ 展开动画流畅

### 交互测试

4. **阈值测试**
   - ✅ 移动4px → 展开
   - ✅ 移动6px → 拖动
   - ✅ 快速点击 → 展开

5. **触摸屏测试** (移动设备)
   - ✅ 触摸拖动正常
   - ✅ 轻触展开正常
   - ✅ 无意外滚动

### 边界测试

6. **视口边界**
   - ✅ 拖到屏幕边缘不会超出
   - ✅ 四个角落都能正常限制

7. **状态切换**
   - ✅ 拖动中点击折叠按钮不会冲突
   - ✅ 展开后再折叠，位置保持

---

## 🎉 完成状态

- ✅ 折叠状态拖动功能已实现
- ✅ 点击/拖动智能区分
- ✅ 视觉反馈完善
- ✅ 边界情况处理
- ✅ 代码已提交并推送

**功能已成功合并到 `ifirefox` 分支并推送到远程! 🎊**

---

## 📝 更新日志链接

- [系统主题切换和聊天框改进](./CHANGELOG_IFIREFOX_MERGE.md)
- [UI修复更新日志](./UI_FIXES_CHANGELOG.md)
- **[本次更新] 折叠状态拖动功能** (当前文档)
