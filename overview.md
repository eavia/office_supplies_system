# 物品仓储管理 — 前端响应式与交互增强概览

> 优化日期: 2026-05-20  
> 技术栈: Django SSR + Bootstrap 5.3 + Font Awesome 6.4 (CSS + 原生 JS)  
> 修改文件: 5 个模板文件

---

## 一、base.html — 全局设计系统增强

### 1.1 新增 CSS 设计令牌

| 类别 | 新增内容 |
|------|---------|
| **平滑滚动** | `html { scroll-behavior: smooth; }` |
| **骨架屏** | `.skeleton` / `.skeleton-text` / `.skeleton-circle` + `@keyframes skeleton-loading` |
| **空状态** | `.empty-state` 统一空数据展示样式 |
| **移动侧边栏** | 增强 `@media (max-width: 768px)` 侧边栏过渡动画 (cubic-bezier)，阴影渐变出现 |
| **侧边栏遮罩** | `.sidebar-backdrop` + `backdrop-filter: blur(2px)` 半透明毛玻璃遮罩 |
| **子菜单动画** | `.fa-chevron-down` 旋转 180° (配合 Bootstrap collapse `aria-expanded`) |
| **顶部栏阴影** | `.topbar.scrolled` — 滚动时阴影加深 |
| **消息提示** | `slideInDown` 入场动画 + `slideOutUp` 自动消失动画 |
| **焦点可见性** | `:focus-visible` 全局 ring 样式，表单控件/按钮/链接分别适配 |
| **微交互** | 统一 `cubic-bezier(0.4, 0, 0.2, 1)` 过渡曲线 |
| **波纹效果** | `.ripple` + `@keyframes ripple-effect` — 表格行点击涟漪 |
| **表单验证** | `.is-valid` / `.is-invalid` 动画反馈 + `shake` 动画 |
| **按钮加载** | `.btn-loading` — 提交按钮 spinner 动画 + 防重复提交 |
| **搜索折叠** | `.search-filter-toggle` / `.search-filter-area` — 移动端筛选区折叠 |
| **分页过渡** | `.page-link:hover` 上浮 + 阴影效果 |
| **快捷操作** | `.quick-action:hover i` 弹性缩放 (cubic-bezier 回弹) |
| **表单区块折叠** | `.form-section-header` / `.form-section-body` 可折叠区块 |
| **卡片链接** | `.card-footer a:hover` 箭头滑动效果 |
| **减弱动画** | `@media (prefers-reduced-motion: reduce)` 全局禁用动画 |
| **打印样式** | `@media print` 隐藏侧边栏/按钮，全宽内容 |

### 1.2 HTML 结构变更

```html
<!-- 新增: 侧边栏遮罩层 (移动端) -->
<div class="sidebar-backdrop" id="sidebarBackdrop"></div>

<!-- 修改: 移动端菜单按钮 -->
<!-- 旧: data-bs-toggle="collapse" data-bs-target="#sidebar" -->
<!-- 新: id="sidebarToggle" aria-label="切换菜单" (JS 控制) -->
<button ... id="sidebarToggle" aria-label="切换菜单">
```

### 1.3 全局 JavaScript (before `</body>`)

| 功能模块 | 说明 |
|---------|------|
| **侧边栏 Offcanvas** | `openSidebar()` / `closeSidebar()` — 移动端滑入 + 遮罩 + body overflow 锁定 + ESC 关闭 + 窗口 resize 自动关闭 |
| **消息自动消失** | 5 秒后 `slideOutUp` 动画 + Bootstrap Alert.close() |
| **顶部栏滚动阴影** | `scroll` 事件监听，`scrollY > 10` 添加 `.scrolled` |
| **表格行波纹** | 全局 `click` 委托，排除链接/按钮/表单元素 |
| **搜索筛选折叠** | `.search-filter-toggle` 点击切换 `.collapsed` / `.expanded` |
| **表单实时验证** | `blur` 事件检查 `[required]` 字段，添加 `.is-valid` / `.is-invalid` |
| **提交按钮防重复** | `submit` 事件添加 `.btn-loading` + `disabled` |
| **表单区块折叠** | `.form-section-header` 点击切换 `.form-section-body.collapsed` |

---

## 二、home.html — 首页交互增强

### 2.1 统计卡片 3D Tilt 效果

- 每个 `.stat-card` 添加 `stat-card-3d` class
- JS 监听 `mousemove`，计算鼠标相对位置，动态设置 `rotateX`/`rotateY` (最大 ±4°)
- 离开时缓动归位
- 触屏设备支持 `touchmove` / `touchend` (最大 ±3°)

### 2.2 快捷操作图标缩放

- CSS: `.quick-action:hover i { transform: scale(1.25); }` — 使用弹性缓动曲线 `cubic-bezier(0.34, 1.56, 0.64, 1)`
- JS: 触屏设备 `touchstart` 缩放到 0.95 + `touchend` 复原

### 2.3 表格行悬浮增强

- 全局 CSS: `transition: background-color 0.2s ease, transform 0.15s ease` + `:active { scale(0.998) }`
- 全局 JS: 点击涟漪效果 (已在 base.html 中实现)

---

## 三、supply_list.html — 列表页面增强

### 3.1 移动端搜索筛选折叠

**结构变更:**
```html
<!-- 旧: 固定排列 -->
<div class="d-flex justify-content-between align-items-center mb-4">
  <div class="btn-group gap-2">...</div>
  <form method="get" class="row g-2">...</form>
</div>

<!-- 新: 响应式折叠 -->
<div class="d-flex justify-content-between align-items-center mb-4 flex-wrap">
  <div class="d-flex align-items-center gap-2">
    <div class="btn-group gap-2">...</div>
    <button class="btn btn-sm btn-outline-secondary search-filter-toggle" type="button">
      <i class="fas fa-filter me-1"></i>展开筛选
    </button>
  </div>
  <div class="search-filter-area collapsed">
    <form method="get" class="row g-2 mt-2 mt-md-0">...</form>
  </div>
</div>
```

- 桌面端 (≥768px): 正常水平排列，toggle 按钮隐藏
- 移动端 (<768px): 筛选区默认折叠，点击按钮展开/收起，按钮文字切换 "展开筛选" ↔ "收起筛选"

### 3.2 表格行波纹效果

- 全局 JS 自动为 `.table-container tbody tr` 添加点击涟漪
- 自动排除链接、按钮、表单元素等交互控件

### 3.3 分页器过渡动画

- CSS: `.page-link:hover` 上浮 1px + 阴影
- CSS: `.page-item.active .page-link` 上浮 + 蓝色阴影

---

## 四、supply_form.html — 表单页面增强

### 4.1 编码信息可折叠区块

```html
<div class="form-section-header" id="codeInfoHeader" role="button" aria-expanded="true">
  <i class="fas fa-info-circle"></i>
  <span>物品编码（主数据）</span>
  <i class="fas fa-chevron-down toggle-icon"></i>
</div>
<div class="form-section-body" id="codeInfoBody">
  <div class="alert alert-info">...</div>
</div>
```

- 点击 header 折叠/展开编码信息区域
- chevron 图标旋转 90° 过渡动画

### 4.2 实时验证反馈

- 全局 JS 对 `[required]` 字段启用 `blur` 验证
- 空值 → `.is-invalid` + `shake` 动画
- 有效值 → `.is-valid` + 绿色边框

### 4.3 提交按钮 Loading

- 全局 JS: 表单提交时添加 `.btn-loading` class
- 显示旋转 spinner，文字隐藏，button disabled 防重复提交

---

## 五、stockin_application_form.html — 入库表单增强

### 5.1 物品明细可折叠区块

```html
<div class="form-section-header" id="itemsSectionHeader" role="button" aria-expanded="true">
  <h5>入库物品明细 <i class="fas fa-chevron-down toggle-icon"></i></h5>
  <button id="addItemBtn" onclick="event.stopPropagation();">添加物品</button>
</div>
<div class="form-section-body" id="itemsSectionBody">
  <!-- 物品动态表格 -->
</div>
```

- 点击标题区域折叠/展开物品明细表
- "添加物品" 按钮使用 `event.stopPropagation()` 避免触发折叠
- 适合长表单场景，减少滚动

### 5.2 其他增强

- 提交按钮 loading 状态 (全局 JS)
- 部门快速搜索字段验证 (全局 JS `[required]` 检测)

---

## 六、可访问性 (Accessibility)

| 特性 | 实现 |
|------|------|
| **减弱动画** | `@media (prefers-reduced-motion: reduce)` — 所有动画时长设为 0.01ms，骨架屏动画移除 |
| **焦点可见** | `:focus-visible` 全局蓝色 ring (2px)，表单控件/按钮/链接分别适配 |
| **键盘导航** | 侧边栏 ESC 关闭，表格行可 Tab 聚焦，ARIA label 更新 |
| **语义 HTML** | `role="button"`, `aria-expanded`, `aria-label` 动态更新 |
| **触屏支持** | 3D tilt 支持 touchmove/touchend，快捷操作 touchstart 反馈，遮罩层滑动关闭 |

---

## 七、浏览器兼容性

| 特性 | Chrome | Firefox | Safari | Edge |
|------|--------|---------|--------|------|
| CSS 变量 | ✅ | ✅ | ✅ | ✅ |
| backdrop-filter | ✅ | ✅ | ✅ (≥9) | ✅ |
| cubic-bezier | ✅ | ✅ | ✅ | ✅ |
| :focus-visible | ✅ | ✅ (≥4) | ✅ (≥15.4) | ✅ |
| prefers-reduced-motion | ✅ | ✅ | ✅ | ✅ |
| transform-style: preserve-3d | ✅ | ✅ | ✅ | ✅ |

---

## 八、文件变更清单

| 文件 | 变更类型 | 主要改动 |
|------|---------|---------|
| `inventory/templates/inventory/base.html` | **大幅增强** | +250 行 CSS、+100 行 JS、HTML 结构调整 |
| `inventory/templates/inventory/home.html` | 中度增强 | stat-card-3d class、+60 行 JS (3D tilt) |
| `inventory/templates/inventory/supply_list.html` | 结构调整 | 搜索筛选区折叠包裹 |
| `inventory/templates/inventory/supply_form.html` | 轻度增强 | 编码信息可折叠区块 |
| `inventory/templates/inventory/stockin_application_form.html` | 轻度增强 | 物品明细可折叠区块 |

---

## 九、测试建议

1. **移动端侧边栏**: 在 375px-768px 宽度测试侧边栏滑入/滑出 + 遮罩点击关闭 + ESC 关闭
2. **消息自动消失**: 触发任意操作产生消息，验证 5 秒后自动消失
3. **3D Tilt**: 桌面端鼠标悬浮统计卡片，移动端触摸滑动
4. **搜索筛选折叠**: 移动端视口验证筛选区默认折叠，点击展开
5. **表单验证**: 留空必填字段后失焦，验证红色抖动反馈
6. **表单提交 Loading**: 点击提交按钮，验证 spinner 出现 + 按钮禁用
7. **减弱动画**: 系统设置开启 "减少动态效果"，验证所有动画停止
8. **键盘导航**: Tab 键遍历页面元素，验证 focus-visible ring 可见
