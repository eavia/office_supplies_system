# -*- coding: utf-8 -*-
"""
办公用品管理系统 - Windows 启动器（系统托盘版）
打包后双击即可运行，自动启动 Django 服务并打开浏览器
隐藏控制台窗口，最小化到系统托盘

错误处理：所有错误写入文件日志，致命错误弹出 Windows 消息框
"""

import os
import sys
import webbrowser
import time
import threading
import socket
import traceback
import io
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# 全局错误日志设置
# ═══════════════════════════════════════════════════════════════

LOG_FILE = None  # 在 get_data_dir() 之后初始化


def _get_data_dir():
    """获取数据存储目录（用户目录，可写）"""
    if sys.platform == 'win32':
        data_dir = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'OfficeSuppliesSystem'
        )
    else:
        data_dir = os.path.join(os.path.expanduser('~'), '.office_supplies_system')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _setup_logging():
    """设置文件日志，同时重定向 stdout/stderr 到日志文件"""
    global LOG_FILE
    data_dir = _get_data_dir()
    LOG_FILE = os.path.join(data_dir, 'launcher.log')

    # 保留原始 stdout/stderr 引用（供 MessageBox 使用）
    if not hasattr(sys, '_original_stdout'):
        sys._original_stdout = sys.stdout
        sys._original_stderr = sys.stderr

    try:
        log_fp = open(LOG_FILE, 'a', encoding='utf-8')
        log_fp.write(f"\n{'='*60}\n")
        log_fp.write(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_fp.write(f"  Python: {sys.version}\n")
        log_fp.write(f"  Platform: {sys.platform}\n")
        log_fp.write(f"  Executable: {sys.executable}\n")
        if hasattr(sys, '_MEIPASS'):
            log_fp.write(f"  MEIPASS: {sys._MEIPASS}\n")
        log_fp.write(f"{'='*60}\n\n")
        log_fp.flush()

        # 重定向 stdout/stderr 到日志文件（仅在无控制台时）
        if sys.platform == 'win32' and not sys.stdout:
            sys.stdout = log_fp
            sys.stderr = log_fp
    except Exception:
        pass  # 日志初始化失败不能阻止启动


def _log(msg):
    """写日志（线程安全尽量简单）"""
    global LOG_FILE
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        line = f"[{timestamp}] {msg}\n"
        if LOG_FILE and os.path.exists(os.path.dirname(LOG_FILE)):
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(line)
    except Exception:
        pass
    # 同时尝试输出到原始 stdout（如果有控制台的话）
    try:
        orig = getattr(sys, '_original_stdout', None)
        if orig:
            orig.write(line)
            orig.flush()
    except Exception:
        pass


def _show_error(title, message):
    """弹出 Windows 错误消息框"""
    _log(f"FATAL: {title}\n{message}")
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x10)  # MB_ICONERROR
        except Exception:
            pass


# 启动时立即设置日志
_setup_logging()


# ═══════════════════════════════════════════════════════════════
# 全局异常捕获（捕获未处理的异常）
# ═══════════════════════════════════════════════════════════════

def _global_exception_handler(exc_type, exc_value, exc_tb):
    """全局未处理异常处理器"""
    tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _log(f"未处理的异常:\n{tb_text}")
    _show_error(
        "办公用品管理系统 - 启动失败",
        f"程序遇到错误，请查看日志文件:\n{LOG_FILE}\n\n"
        f"错误: {exc_type.__name__}: {exc_value}\n\n"
        f"详细信息:\n{tb_text[-500:]}"
    )


sys.excepthook = _global_exception_handler


# ═══════════════════════════════════════════════════════════════
# 系统托盘 (pystray + Pillow)
# ═══════════════════════════════════════════════════════════════

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
    _log("pystray + Pillow 已加载，系统托盘可用")
except ImportError as e:
    TRAY_AVAILABLE = False
    _log(f"pystray/Pillow 不可用: {e}")


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def get_resource_path(relative_path):
    """获取资源文件路径（支持开发环境和 PyInstaller 打包环境）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def check_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def find_free_port(start_port=8000, max_port=9000):
    """查找可用端口"""
    for port in range(start_port, max_port):
        if check_port_available(port):
            return port
    return None


def wait_for_server(port, timeout=30):
    """等待服务器启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', port))
                return True
        except Exception:
            time.sleep(0.5)
    return False


# ═══════════════════════════════════════════════════════════════
# Django 初始化
# ═══════════════════════════════════════════════════════════════

def setup_django_env():
    """设置 Django 环境变量"""
    data_dir = _get_data_dir()
    db_path = os.path.join(data_dir, 'db.sqlite3')
    static_root = get_resource_path('staticfiles')
    project_dir = get_resource_path('.')

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    os.environ['DJANGO_DB_PATH'] = db_path
    os.environ['DJANGO_STATIC_ROOT'] = static_root
    sys.path.insert(0, project_dir)

    _log(f"DB路径: {db_path}")
    _log(f"静态文件: {static_root}")
    _log(f"项目目录: {project_dir}")
    _log(f"sys.path[0]: {sys.path[0]}")


def run_migrations():
    """运行数据库迁移"""
    try:
        import django
        django.setup()
        from django.core.management import call_command
        call_command('migrate', '--run-syncdb', verbosity=0)
        _log("数据库迁移完成")
    except Exception as e:
        _log(f"数据库迁移警告: {e}")
        # 不终止 — 可能是首次启动，继续尝试


def create_default_admin():
    """创建默认管理员账户"""
    try:
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            _log("默认管理员账户已创建: admin / admin123")
        else:
            _log("管理员账户已存在，跳过创建")
    except Exception as e:
        _log(f"创建管理员警告: {e}")


# ═══════════════════════════════════════════════════════════════
# 托盘图标
# ═══════════════════════════════════════════════════════════════

def create_icon_image():
    """生成托盘图标（蓝底白字"办"）"""
    width = 64
    height = 64
    image = Image.new('RGBA', (width, height), (0, 120, 212, 255))
    dc = ImageDraw.Draw(image)
    try:
        dc.rounded_rectangle([4, 4, 60, 60], radius=8, fill=(255, 255, 255, 255))
        dc.text((width // 2, height // 2), "办", fill=(0, 120, 212, 255),
                anchor="mm", font_size=36)
    except Exception:
        dc.text((16, 12), "办", fill=(0, 120, 212, 255))
    return image


# ═══════════════════════════════════════════════════════════════
# 托盘应用主类
# ═══════════════════════════════════════════════════════════════

class TrayApp:
    def __init__(self):
        self.port = None
        self.icon = None
        self.server_thread = None
        self.running = True

    def open_browser(self, icon=None, item=None):
        """打开浏览器"""
        if self.port:
            url = f'http://127.0.0.1:{self.port}'
            _log(f"打开浏览器: {url}")
            webbrowser.open(url)

    def stop_server(self, icon=None, item=None):
        """停止服务并退出"""
        _log("用户请求退出")
        self.running = False
        if self.icon:
            self.icon.stop()
        os._exit(0)

    def start_server(self):
        """启动 Django 服务器"""
        _log("开始启动 Django 服务器...")

        setup_django_env()

        # 查找可用端口
        self.port = find_free_port(8000)
        if not self.port:
            _log("错误: 找不到可用端口 (8000-9000)")
            _show_error("端口冲突",
                        "无法在 8000-9000 范围内找到可用端口。\n"
                        "请关闭占用端口的程序后重试。")
            return False
        _log(f"使用端口: {self.port}")

        # 运行迁移
        _log("运行数据库迁移...")
        run_migrations()

        # 创建默认管理员
        create_default_admin()

        # 启动 Django 开发服务器
        def run_django():
            try:
                import django
                django.setup()
                from django.core.management import call_command
                call_command('runserver', f'0.0.0.0:{self.port}', '--noreload')
            except Exception as e:
                _log(f"Django runserver 异常: {traceback.format_exc()}")

        self.server_thread = threading.Thread(target=run_django, daemon=True)
        self.server_thread.start()

        # 等待服务器就绪
        _log("等待服务器就绪...")
        if wait_for_server(self.port, timeout=30):
            _log(f"服务器启动成功: http://127.0.0.1:{self.port}")
            webbrowser.open(f'http://127.0.0.1:{self.port}')
            return True
        else:
            _log("错误: 服务器启动超时 (30秒)")
            _show_error("启动超时",
                        "Django 服务器未能在 30 秒内启动。\n"
                        f"请查看日志: {LOG_FILE}")
            return False

    def run(self):
        """主运行循环"""
        _log("TrayApp.run() 开始")

        # 检查是否已有实例运行
        if not check_port_available(8000):
            _log("端口 8000 已被占用，可能已有实例运行")
            webbrowser.open('http://127.0.0.1:8000')
            return

        # 启动服务器
        if not self.start_server():
            _log("服务器启动失败，退出")
            return

        if not TRAY_AVAILABLE:
            _log("无系统托盘支持，保持后台运行")
            while self.running:
                time.sleep(1)
            return

        # 创建托盘图标
        try:
            icon_image = create_icon_image()
        except Exception as e:
            _log(f"创建图标失败: {e}")
            icon_image = Image.new('RGBA', (64, 64), (0, 120, 212, 255))

        menu = pystray.Menu(
            pystray.MenuItem("打开浏览器", self.open_browser, default=True),
            pystray.MenuItem("访问地址", pystray.Menu(
                pystray.MenuItem(f"http://127.0.0.1:{self.port}", self.open_browser)
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.stop_server),
        )

        self.icon = pystray.Icon(
            "OfficeSuppliesSystem",
            icon_image,
            f"办公用品管理系统 (端口 {self.port})",
            menu
        )
        _log("系统托盘已创建，进入事件循环")
        self.icon.run()


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    try:
        _log("程序启动")
        app = TrayApp()
        app.run()
    except Exception as e:
        _log(f"main() 异常: {traceback.format_exc()}")
        _show_error("启动失败",
                    f"程序启动时发生错误:\n\n{e}\n\n"
                    f"详细日志: {LOG_FILE}")


if __name__ == '__main__':
    main()
