# -*- coding: utf-8 -*-
"""
物品仓储管理 - Windows 启动器（简化版）
打包后双击即可运行，自动启动 Django 服务并打开浏览器
"""

import os
import sys
import webbrowser
import time
import threading
import socket

def get_resource_path(relative_path):
    """获取资源文件路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def check_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0

def wait_for_server(port, timeout=30):
    """等待服务器启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', port))
                return True
        except:
            time.sleep(0.5)
    return False

def main():
    """主函数"""
    # 设置 Django 环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # 添加项目目录到路径
    project_dir = get_resource_path('.')
    sys.path.insert(0, project_dir)
    
    print("=" * 60)
    print("  物品仓储管理")
    print("=" * 60)
    print()
    
    # 检查是否已有实例运行
    if not check_port_available(8000):
        print("系统已在运行，正在打开浏览器...")
        webbrowser.open('http://127.0.0.1:8000')
        return
    
    try:
        import django
        django.setup()
        
        from django.core.management import call_command
        from django.contrib.auth import get_user_model
        
        print("正在初始化数据库...")
        call_command('migrate', '--run-syncdb', verbosity=0)
        
        # 创建默认管理员
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            print("已创建默认管理员: admin / admin123")
        
        print("正在启动服务器...")
        print("访问地址: http://127.0.0.1:8000")
        print()
        
        # 在新线程启动服务器
        def run_server():
            call_command('runserver', '0.0.0.0:8000', '--noreload')
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # 等待服务器启动
        if wait_for_server(8000):
            print("服务器启动成功！正在打开浏览器...")
            webbrowser.open('http://127.0.0.1:8000')
            print()
            print("按 Ctrl+C 停止服务")
            
            # 保持运行
            while True:
                time.sleep(1)
        else:
            print("服务器启动超时")
            
    except KeyboardInterrupt:
        print("\n正在停止服务...")
    except Exception as e:
        print(f"错误: {e}")
        input("按回车键退出...")

if __name__ == '__main__':
    main()
