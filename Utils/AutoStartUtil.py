import os
import time
import subprocess
import threading
from pathlib import Path


class AutoStartUtil:
    """
    Windows自启动工具类
    功能：设置/取消程序自启动，运行完成后自动清理bat文件
    """

    def __init__(self, app_name="MyApp", app_path=None):
        """
        初始化自启动工具

        Args:
            app_name (str): 应用名称，用于注册表键名
            app_path (str): 应用程序路径，如果为None则使用当前脚本路径
        """
        self.app_name = app_name
        self.app_path = app_path or os.path.abspath(__file__)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.set_bat_path = os.path.join(self.script_dir, "set_autostart.bat")
        self.unset_bat_path = os.path.join(self.script_dir, "unset_autostart.bat")
        self.completion_flag = os.path.join(self.script_dir, "autostart_completed")

    def _create_set_autostart_bat(self):
        """创建设置自启动的BAT文件"""

        content = f'''@echo off
:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 需要管理员权限，正在重新启动...
    powershell -Command "Start-Process cmd -ArgumentList '/c \\"%~f0\\"' -Verb RunAs"
    exit /b
)

echo 设置自启动中...
reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "{self.app_name}" /t REG_SZ /d "{escaped_path}" /f

if %errorlevel% equ 0 (
    echo 自启动设置成功！
    echo 程序：{self.app_name}
    echo 路径：{self.app_path}
) else (
    echo 自启动设置失败！
)

echo completed > "%~dp0autostart_completed"
timeout /t 2 /nobreak >nul
'''

        with open(self.set_bat_path, 'w', encoding='gbk') as f:
            f.write(content)

    def _create_unset_autostart_bat(self):
        """创建取消自启动的BAT文件"""
        content = f'''@echo off
:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 需要管理员权限，正在重新启动...
    powershell -Command "Start-Process cmd -ArgumentList '/c \\"%~f0\\"' -Verb RunAs"
    exit /b
)

echo 取消自启动中...
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "{self.app_name}" /f

if %errorlevel% equ 0 (
    echo 自启动取消成功！
    echo 程序：{self.app_name}
) else (
    echo 自启动取消失败或该项不存在！
)

echo completed > "%~dp0autostart_completed"
timeout /t 2 /nobreak >nul
'''

        with open(self.unset_bat_path, 'w', encoding='gbk') as f:
            f.write(content)

    def _wait_for_completion_and_cleanup(self, bat_path, timeout=30):
        """
        等待BAT文件执行完成并清理文件

        Args:
            bat_path (str): BAT文件路径
            timeout (int): 超时时间（秒）
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if os.path.exists(self.completion_flag):
                # 等待一下确保文件写入完成
                time.sleep(0.5)
                break
            time.sleep(0.1)

        # 清理文件
        self._cleanup_files(bat_path)

    def _cleanup_files(self, bat_path):
        """
        清理临时文件

        Args:
            bat_path (str): BAT文件路径
        """
        files_to_remove = [bat_path, self.completion_flag]

        for file_path in files_to_remove:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"已清理文件: {file_path}")
            except Exception as e:
                print(f"清理文件失败 {file_path}: {e}")

    def set_autostart(self, show_window=True):
        """
        设置程序自启动

        Args:
            show_window (bool): 是否显示命令窗口

        Returns:
            bool: 操作是否成功
        """
        try:
            # 创建BAT文件
            self._create_set_autostart_bat()

            # 执行BAT文件
            if show_window:
                subprocess.Popen([self.set_bat_path], shell=True)
            else:
                subprocess.Popen([self.set_bat_path], shell=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)

            # 启动后台线程进行清理
            cleanup_thread = threading.Thread(
                target=self._wait_for_completion_and_cleanup,
                args=(self.set_bat_path,),
                daemon=True
            )
            cleanup_thread.start()

            print(f"正在设置 {self.app_name} 自启动...")
            return True

        except Exception as e:
            print(f"设置自启动失败: {e}")
            return False

    def unset_autostart(self, show_window=True):
        """
        取消程序自启动

        Args:
            show_window (bool): 是否显示命令窗口

        Returns:
            bool: 操作是否成功
        """
        try:
            # 创建BAT文件
            self._create_unset_autostart_bat()

            # 执行BAT文件
            if show_window:
                subprocess.Popen([self.unset_bat_path], shell=True)
            else:
                subprocess.Popen([self.unset_bat_path], shell=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)

            # 启动后台线程进行清理
            cleanup_thread = threading.Thread(
                target=self._wait_for_completion_and_cleanup,
                args=(self.unset_bat_path,),
                daemon=True
            )
            cleanup_thread.start()

            print(f"正在取消 {self.app_name} 自启动...")
            return True

        except Exception as e:
            print(f"取消自启动失败: {e}")
            return False

    def check_autostart_status(self):
        """
        检查程序是否已设置自启动

        Returns:
            bool: 是否已设置自启动
        """
        try:
            import winreg

            # 打开注册表键
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )

            try:
                # 尝试读取值
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False

        except Exception as e:
            print(f"检查自启动状态失败: {e}")
            return False

    def get_autostart_path(self):
        """
        获取注册表中的自启动路径

        Returns:
            str: 自启动路径，如果未设置则返回None
        """
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )

            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return value
            except FileNotFoundError:
                winreg.CloseKey(key)
                return None

        except Exception as e:
            print(f"获取自启动路径失败: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    # 创建自启动工具实例
    autostart = AutoStartUtil(
        app_name="MyApplication",
        app_path=r"C:\Program Files\MyApp\myapp.exe"
    )

    # 检查当前状态
    print(f"当前自启动状态: {'已设置' if autostart.check_autostart_status() else '未设置'}")

    # 获取自启动路径
    current_path = autostart.get_autostart_path()
    if current_path:
        print(f"当前自启动路径: {current_path}")

    # 设置自启动
    print("\n=== 设置自启动 ===")
    autostart.set_autostart(show_window=True)

    # 等待几秒让用户看到结果
    time.sleep(5)

    # 取消自启动
    print("\n=== 取消自启动 ===")
    autostart.unset_autostart(show_window=True)

    # 最终检查
    time.sleep(3)
    print(f"\n最终状态: {'已设置' if autostart.check_autostart_status() else '未设置'}")
