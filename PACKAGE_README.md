# 物品仓储管理 - Windows 打包说明

## 打包步骤

### 方法一：使用脚本打包（推荐）

#### Linux/macOS:
```bash
cd office_supplies_system
chmod +x build_exe.sh
./build_exe.sh
```

#### Windows:
```cmd
cd office_supplies_system
build_exe.bat
```

### 方法二：手动打包

1. **安装依赖**
```bash
pip install pyinstaller openpyxl
```

2. **创建初始数据库**
```bash
python manage.py migrate
python manage.py createsuperuser
```

3. **执行打包**
```bash
# 使用简化版启动器
pyinstaller --name="物品仓储管理" \
  --onefile \
  --console \
  --add-data="inventory/templates;inventory/templates" \
  --add-data="inventory/migrations;inventory/migrations" \
  --add-data="db.sqlite3;." \
  --hidden-import=django \
  --hidden-import=openpyxl \
  --hidden-import=inventory \
  launcher_simple.py
```

## 打包输出

打包完成后，`dist/` 目录下会生成：
- `物品仓储管理.exe` - 可执行文件

## 使用方法

1. **复制到目标电脑**
   - 将 `物品仓储管理.exe` 复制到 Windows 电脑

2. **运行**
   - 双击 `物品仓储管理.exe`
   - 程序会自动启动服务器并打开浏览器

3. **登录**
   - 用户名: `admin`
   - 密码: `admin123`

4. **数据存储**
   - 数据库存储在: `%APPDATA%\OfficeSuppliesSystem\db.sqlite3`
   - 即使删除 exe 文件，数据也不会丢失

## 注意事项

1. **首次运行较慢**：需要解压资源文件
2. **杀毒软件误报**：部分杀毒软件可能误报，请添加信任
3. **端口占用**：如果 8000 端口被占用，程序会自动提示
4. **数据备份**：定期备份 `%APPDATA%\OfficeSuppliesSystem\` 目录

## 文件说明

| 文件 | 说明 |
|------|------|
| `launcher.py` | 完整版启动器（支持数据目录自定义） |
| `launcher_simple.py` | 简化版启动器（打包用） |
| `launcher.spec` | PyInstaller 配置文件 |
| `build_exe.sh` | Linux/macOS 打包脚本 |
| `build_exe.bat` | Windows 打包脚本 |

## 技术说明

- **打包原理**：PyInstaller 将 Python 解释器、Django 框架和项目代码打包成独立 exe
- **数据库位置**：使用 `%APPDATA%` 目录存储数据，保证可写性
- **自动迁移**：启动时自动执行数据库迁移
- **自动创建管理员**：首次运行时自动创建默认管理员账户
