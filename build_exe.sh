#!/bin/bash
# 办公用品管理系统 - PyInstaller 打包脚本
# 此脚本将项目打包成独立的 Windows 可执行文件

echo "=========================================="
echo "  办公用品管理系统 - 打包工具"
echo "=========================================="
echo ""

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "正在激活虚拟环境..."
    source venv/bin/activate
fi

# 安装必要的打包工具
echo "检查打包工具..."
pip install -q pyinstaller openpyxl

# 创建初始数据库（如果尚未创建）
echo "准备数据库..."
if [ ! -f "db.sqlite3" ]; then
    echo "创建初始数据库..."
    python manage.py migrate --run-syncdb
    echo "创建管理员账户..."
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('管理员账户已创建: admin / admin123')
EOF
fi

# 收集静态文件（如果需要）
# echo "收集静态文件..."
# python manage.py collectstatic --noinput

# 执行打包
echo ""
echo "开始打包..."
echo "此过程可能需要几分钟，请耐心等待..."
echo ""

pyinstaller launcher.spec \
    --clean \
    --noconfirm \
    --log-level=WARN

# 检查打包结果
if [ -d "dist/办公用品管理系统" ] || [ -f "dist/办公用品管理系统.exe" ]; then
    echo ""
    echo "=========================================="
    echo "  打包成功！"
    echo "=========================================="
    echo ""
    echo "输出目录: ./dist/"
    echo ""
    echo "使用说明:"
    echo "1. 将 dist/办公用品管理系统.exe 复制到目标电脑"
    echo "2. 双击运行即可启动系统"
    echo "3. 系统会自动在浏览器中打开"
    echo ""
    echo "默认登录:"
    echo "  用户名: admin"
    echo "  密码: admin123"
    echo ""
    echo "数据存储位置:"
    echo "  Windows: %APPDATA%/OfficeSuppliesSystem/"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "  打包可能失败，请检查错误信息"
    echo "=========================================="
fi

# 可选：创建压缩包
read -p "是否创建压缩包？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "创建压缩包..."
    cd dist
    zip -r "办公用品管理系统-$(date +%Y%m%d).zip" "办公用品管理系统" "办公用品管理系统.exe" 2>/dev/null || \
    tar -czf "办公用品管理系统-$(date +%Y%m%d).tar.gz" "办公用品管理系统" "办公用品管理系统.exe" 2>/dev/null || \
    echo "压缩失败，请手动打包 dist/ 目录"
    cd ..
fi

echo ""
echo "完成！"
