# 办公用品管理系统 (Django + SQLite)

基于 Django 6.0 + SQLite 的办公用品管理系统，包含四大核心模块。

## 系统功能

### 1. 办公用品申请
- 库存一览（查询/登记/追加/变更/删除）
- 归还申请

### 2. 出入库管理
- 入库申请（登记/查询/变更/删除）
- 出库记录（登记/查询）
- 入出库审批（批准/拒绝）
- 入库统计
- 出库统计

### 3. IT设备管理
- 计算机资源一览（主机/显示器登记/变更/删除）
- 计算机类型一览（追加/变更/删除）

### 4. 基础数据
- 办公用品库存表
- 入库申请表
- 出库记录表
- IT设备表
- 计算机类型表

## 技术栈

- **后端框架**: Django 6.0
- **数据库**: SQLite3
- **前端**: Bootstrap 5 + Font Awesome
- **Python**: 3.8+

## 快速启动

### 方式一：使用服务管控脚本（推荐）

```bash
cd office_supplies_system
chmod +x runserver_ctl.sh
./runserver_ctl.sh start
./runserver_ctl.sh status
```

常用命令：

```bash
./runserver_ctl.sh stop
./runserver_ctl.sh restart
./runserver_ctl.sh logs
```

### 方式二：使用启动脚本

```bash
cd office_supplies_system
chmod +x start.sh
./start.sh
```

### 方式三：手动启动

```bash
cd office_supplies_system
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser  # 创建管理员
python manage.py runserver
```

## 访问地址

- **系统首页**: http://127.0.0.1:8000
- **管理后台**: http://127.0.0.1:8000/admin

## 默认账户

- 用户名: `admin`
- 密码: `admin123`

## Excel 导入导出功能

### 办公用品库存表
- **导出**: 访问 `/supplies/export/` 或点击库存列表页【导出】按钮
- **导入**: 访问 `/supplies/import/` 或点击库存列表页【导入】按钮
- **模板下载**: 访问 `/supplies/template/` 或在导入页面点击【下载导入模板】

**Excel 格式要求 (办公用品)**:
| 列 | 字段 | 说明 |
|----|-----|------|
| A | 物品编码 | 必填，唯一标识 |
| B | 物品名称 | 必填 |
| C | 类别 | 如：文具、耗材、设备 |
| D | 规格型号 | 可选 |
| E | 单位 | 默认：个 |
| F | 库存数量 | 数字 |
| G | 安全库存 | 数字，默认：10 |
| H | 存放位置 | 可选 |
| I | 供应商 | 可选 |
| J | 单价 | 数字 |
| K | 状态 | 正常/低库存/停用 |

### IT设备表
- **导出**: 访问 `/devices/export/` 或点击设备列表页【导出】按钮
- **导入**: 访问 `/devices/import/` 或点击设备列表页【导入】按钮
- **模板下载**: 访问 `/devices/template/` 或在导入页面点击【下载导入模板】

**Excel 格式要求 (IT设备)**:
| 列 | 字段 | 说明 |
|----|-----|------|
| A | 设备编号 | 必填，唯一标识 |
| B | 设备类型 | 必填，如：台式机、笔记本 |
| C | 资产编号 | 可选 |
| D | 序列号 | 可选 |
| E | 采购日期 | 格式：YYYY-MM-DD |
| F | 采购价格 | 数字 |
| G | 存放位置 | 可选 |
| H | 使用人 | 可选 |
| I | 使用部门 | 可选 |
| J | 状态 | 库存/使用中/维修中/报废 |
| K | 备注 | 可选 |

**导入选项**:
- 【更新已存在记录】勾选后，如果编码/编号已存在则更新数据，否则新增

**导入时类别自动创建**:
- 导入办公用品时，如果填写的类别名称在系统中不存在，会自动创建该类别
- 自动创建的类别编码格式为：`CAT001`、`CAT002` 等
- 建议预先在【类别管理】页面维护好标准类别列表，避免重复或相似的类别名称

**模板文件说明**:
- 模板包含表头和3行示例数据（灰色斜体）
- 附带"填写说明"工作表，详细说明每个字段的填写规则
- 导入前请删除示例数据行

## 办公用品类别管理

系统提供办公用品类别标准化管理功能：

### 功能说明
- **类别一览**: `/supply-categories/` - 查看所有类别，支持排序
- **类别追加**: `/supply-categories/create/` - 添加新类别
- **类别变更**: `/supply-categories/{id}/update/` - 修改类别信息
- **类别删除**: `/supply-categories/{id}/delete/` - 删除类别（有关联物品时不可删除）

### 类别字段
| 字段 | 说明 |
|-----|------|
| 类别编码 | 唯一标识，如：WJ、HC、SB |
| 类别名称 | 显示名称，如：文具、耗材、设备 |
| 类别说明 | 描述信息 |
| 排序 | 数字越小越靠前 |

### 类别使用流程
1. 进入【类别管理】页面维护标准类别列表
2. 在办公用品登记或导入时选择/填写类别
3. 导入时若类别不存在，系统自动创建

## 项目结构

```
office_supplies_system/
├── config/                 # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── inventory/              # 主应用
│   ├── models.py          # 数据模型
│   ├── views.py            # 视图函数
│   ├── forms.py            # 表单
│   ├── urls.py             # URL路由
│   ├── admin.py            # 管理后台
│   └── templates/          # HTML模板
│       └── inventory/
│           ├── base.html
│           └── ...
├── venv/                   # Python 虚拟环境
├── db.sqlite3              # SQLite 数据库
├── runserver_ctl.sh        # 服务管控脚本（start/stop/restart/status/logs）
└── start.sh                # 初始化启动脚本
```

## 功能列表

| 模块 | 功能 | URL |
|------|------|-----|
| 首页 | 系统首页 | `/` |
| 库存管理 | 库存一览 | `/supplies/` |
| | 入库登记 | `/supplies/create/` |
| | 库存变更 | `/supplies/<id>/update/` |
| | 库存追加 | `/supplies/<id>/add-stock/` |
| | 删除库存 | `/supplies/<id>/delete/` |
| | **导出Excel** | `/supplies/export/` |
| | **导入Excel** | `/supplies/import/` |
| | **下载模板** | `/supplies/template/` |
| | **类别管理** | `/supply-categories/` |
| | 类别追加 | `/supply-categories/create/` |
| 入库申请 | 申请查询 | `/stockin/applications/` |
| | 新增申请 | `/stockin/applications/create/` |
| | 审批列表 | `/approvals/` |
| | 审批处理 | `/approvals/<id>/process/` |
| 出库管理 | 出库记录 | `/stockout/` |
| | 出库登记 | `/stockout/create/` |
| 归还申请 | 归还列表 | `/returns/` |
| | 新增归还 | `/returns/create/` |
| IT设备 | 设备列表 | `/devices/` |
| | 设备登记 | `/devices/create/` |
| | 设备变更 | `/devices/<id>/update/` |
| | 删除设备 | `/devices/<id>/delete/` |
| | **导出Excel** | `/devices/export/` |
| | **导入Excel** | `/devices/import/` |
| | **下载模板** | `/devices/template/` |
| 类型管理 | 类型列表 | `/computer-types/` |
| | 类型追加 | `/computer-types/create/` |
| | 类型变更 | `/computer-types/<id>/update/` |
| | 删除类型 | `/computer-types/<id>/delete/` |
| 统计报表 | 入库统计 | `/statistics/stockin/` |
| | 出库统计 | `/statistics/stockout/` |

## 开发说明

### 创建新的迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

### 创建管理员
```bash
python manage.py createsuperuser
```

### 收集静态文件
```bash
python manage.py collectstatic
```
