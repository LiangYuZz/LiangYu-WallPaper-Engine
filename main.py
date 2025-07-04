import os
import sys
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFileDialog,
                             QCheckBox, QMessageBox, QSystemTrayIcon, QMenu, QAction, QDialog, QListWidget,
                             QListWidgetItem, QScrollArea, QStyle)
from PyQt5.QtCore import Qt, QSettings, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush
import winreg
import time
import psutil
import importlib
import importlib.util
import traceback
from abc import ABC, abstractmethod

from Utils.AutoStartUtil import AutoStartUtil
from plugin_base import PluginBase
import Utils.AutoStartUtil

class PluginManager:
    """插件管理器"""

    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.plugins = []
        self.plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.ensure_plugin_dir()

    def ensure_plugin_dir(self):
        """确保插件目录存在"""
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            # 创建示例插件



    def load_plugins(self):
        """加载所有插件"""
        self.plugins.clear()

        if not os.path.exists(self.plugin_dir):
            return

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    self.load_plugin(filename)
                except Exception as e:
                    print(f"加载插件 {filename} 失败: {e}")
                    traceback.print_exc()

    def load_plugin(self, filename):
        """加载单个插件"""
        plugin_path = os.path.join(self.plugin_dir, filename)
        plugin_name = filename[:-3]  # 去掉.py扩展名

        # 动态导入插件模块
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 创建插件实例
        if hasattr(module, 'create_plugin'):
            plugin = module.create_plugin()
            if isinstance(plugin, PluginBase):
                plugin.initialize(self.app_instance)
                self.plugins.append(plugin)
                # 加载保存的插件状态
                settings = QSettings("VideoWallpaper", "Settings")
                enabled = settings.value(f"plugins/{plugin.name}/enabled", True, type=bool)
                plugin.enabled = enabled
                print(f"成功加载插件: {plugin.name} v{plugin.version} (启用状态: {plugin.enabled})")
            else:
                print(f"插件 {filename} 不是有效的插件类")
        else:
            print(f"插件 {filename} 缺少 create_plugin 函数")

    def trigger_wallpaper_start(self, video_path, loop):
        """触发壁纸启动事件"""
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    plugin.on_wallpaper_start(video_path, loop)
                except Exception as e:
                    print(f"插件 {plugin.name} 处理壁纸启动事件时出错: {e}")

    def trigger_wallpaper_stop(self):
        """触发壁纸停止事件"""
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    plugin.on_wallpaper_stop()
                except Exception as e:
                    print(f"插件 {plugin.name} 处理壁纸停止事件时出错: {e}")

    def trigger_settings_changed(self, settings):
        """触发设置更改事件"""
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    plugin.on_settings_changed(settings)
                except Exception as e:
                    print(f"插件 {plugin.name} 处理设置更改事件时出错: {e}")

    def trigger_operate_on_window(self, window):
        """触发插件操作窗口事件"""
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    plugin.operate_on_window(window)
                except Exception as e:
                    print(f"插件 {plugin.name} 操作窗口时出错: {e}")

    def cleanup_plugins(self):
        """清理所有插件"""
        for plugin in self.plugins:
            try:
                plugin.cleanup()
            except Exception as e:
                print(f"清理插件 {plugin.name} 时出错: {e}")


class VideoWallpaper(QWidget):
    def __init__(self, video_path, loop=True, plugin_manager=None):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.video_path = video_path
        self.loop = loop
        self.is_wallpaper_set = False
        self.original_parent = ctypes.windll.user32.GetParent(int(self.winId()))  # 保存原始父窗口

        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        # 设置主窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnBottomHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 允许鼠标事件
        self.setGeometry(screen_geometry)

        # 创建透明的覆盖窗口用于插件控件
        self.widget_overlay = QWidget()
        # 在 VideoWallpaper 类的 __init__ 方法中，修改覆盖层设置
        self.widget_overlay.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus  # 添加这行
        )

        self.widget_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.widget_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.widget_overlay.setGeometry(screen_geometry)

        # 初始化VLC
        try:
            import vlc
            self.instance = vlc.Instance("--no-xlib")
            self.mlist_player = self.instance.media_list_player_new()
            media_list = self.instance.media_list_new([self.video_path])
            self.mlist_player.set_media_list(media_list)
            self.media_player = self.instance.media_player_new()
            self.media_player.set_hwnd(int(self.winId()))
            self.mlist_player.set_media_player(self.media_player)
            self.mlist_player.set_playback_mode(vlc.PlaybackMode.loop if self.loop else vlc.PlaybackMode.default)
            self.mlist_player.play()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法初始化VLC播放器: {str(e)}")
            self.close()
            return

        # 将窗口设置为壁纸
        self._set_as_wallpaper()

        # 如果设置壁纸成功，则显示控件覆盖层并通知插件
        if self.is_wallpaper_set and self.plugin_manager:
            self.widget_overlay.show()
            self.plugin_manager.trigger_operate_on_window(self.widget_overlay)

    def _find_workerw(self):
        """查找 WorkerW 窗口句柄 """
        progman = ctypes.windll.user32.FindWindowW("Progman", None)
        result = ctypes.wintypes.DWORD()
        ctypes.windll.user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0x0002, 1000, ctypes.byref(result))

        workerw = None

        def enum_windows_proc(hwnd, lParam):
            nonlocal workerw
            if ctypes.windll.user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
                workerw_candidate = ctypes.windll.user32.FindWindowExW(None, hwnd, "WorkerW", None)
                if workerw_candidate:
                    workerw = workerw_candidate
                    return False  # Stop enumeration
            return True

        enum_func = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        ctypes.windll.user32.EnumWindows(enum_func(enum_windows_proc), 0)

        return workerw

    def _set_as_wallpaper(self):
        """使用Windows API将窗口设置为壁纸"""
        try:
            workerw = self._find_workerw()
            if workerw:
                # 将视频窗口和控件覆盖窗口都设置为 WorkerW 的子窗口
                ctypes.windll.user32.SetParent(int(self.winId()), workerw)
                ctypes.windll.user32.SetParent(int(self.widget_overlay.winId()), workerw)

                # 调整窗口Z序，确保覆盖窗口在视频窗口之上
                ctypes.windll.user32.SetWindowPos(
                    int(self.widget_overlay.winId()),
                    -1,  # HWND_TOP
                    0, 0, 0, 0,
                    0x0001 | 0x0002  # SWP_NOMOVE | SWP_NOSIZE
                )

                self.is_wallpaper_set = True
                print(f"成功设置为壁纸，WorkerW句柄: {workerw}")
            else:
                print("警告：未找到WorkerW窗口，可能无法正确设置壁纸")
                QMessageBox.warning(self, "错误", "无法将窗口嵌入桌面。")
                self.close()
        except Exception as e:
            print(f"设置壁纸时出错: {e}")
            self.close()

    def stop_wallpaper(self):
        """停止壁纸播放并关闭所有窗口"""
        try:
            if hasattr(self, 'mlist_player'):
                self.mlist_player.stop()
            if hasattr(self, 'media_player'):
                self.media_player.stop()

            # 关闭控件覆盖窗口
            if hasattr(self, 'widget_overlay'):
                self.widget_overlay.close()

            # 恢复窗口父级关系
            if self.is_wallpaper_set:
                ctypes.windll.user32.SetParent(int(self.winId()), self.original_parent or 0)

            self.close()  # 关闭视频窗口
            print("壁纸已停止")
            return True
        except Exception as e:
            print(f"停止壁纸时出错: {e}")
            return False

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 释放VLC资源
        try:
            if hasattr(self, 'mlist_player'):
                self.mlist_player.release()
            if hasattr(self, 'media_player'):
                self.media_player.release()
            if hasattr(self, 'instance'):
                self.instance.release()
        except Exception as e:
            print(f"释放VLC资源时出错: {e}")

        # 确保控件覆盖层也已关闭
        if hasattr(self, 'widget_overlay'):
            self.widget_overlay.deleteLater()

        event.accept()


class PluginInfoDialog(QDialog):
    def __init__(self, plugin_manager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.setWindowTitle("插件信息")
        self.resize(700, 500)

        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)

        self.list_widget = QListWidget()
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setWordWrap(True)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        for plugin in self.plugin_manager.plugins:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)

            checkbox = QCheckBox(f"{plugin.name} v{plugin.version}")
            checkbox.setStyleSheet("font-weight: bold;")
            checkbox.setChecked(plugin.enabled)
            checkbox.stateChanged.connect(lambda state, p=plugin: self.toggle_plugin(p, state))

            author_label = QLabel(f"作者: {plugin.author}")
            desc_label = QLabel(f"描述: {plugin.description}")
            desc_label.setWordWrap(True)

            item_layout.addWidget(checkbox)
            item_layout.addWidget(author_label)
            item_layout.addWidget(desc_label)

            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)

            # Store plugin reference in item for context menu
            item.setData(Qt.UserRole, plugin)

        scroll_layout.addWidget(self.list_widget)
        main_layout.addWidget(scroll_area)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        # 添加最小化事件处理
        self.setWindowTitle("LiangYuPaper")
        self.setFixedSize(550, 450)

        # 新增：设置窗口最小化事件过滤器
        self.installEventFilter(self)

    # 新增：事件过滤器处理最小化事件
    def eventFilter(self, obj, event):
        if obj == self and event.type() == event.WindowStateChange:
            # 当窗口被最小化且启用了"最小化到托盘"选项时
            if self.isMinimized() and self.minimize_to_tray_check.isChecked():
                self.hide()  # 隐藏窗口
                self.tray_icon.showMessage(
                    "已最小化",
                    "程序已最小化到系统托盘",
                    QSystemTrayIcon.Information,
                    2000
                )
        return super().eventFilter(obj, event)

    def toggle_plugin(self, plugin, state):
        plugin.enabled = state == Qt.Checked
        settings = QSettings("VideoWallpaper", "Settings")
        settings.setValue(f"plugins/{plugin.name}/enabled", plugin.enabled)

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item:
            plugin = item.data(Qt.UserRole)
            if plugin and hasattr(plugin, 'show_settings_dialog'):
                menu = QMenu(self)
                settings_action = QAction("设置", self)
                settings_action.triggered.connect(plugin.show_settings_dialog)
                menu.addAction(settings_action)
                menu.exec_(self.list_widget.mapToGlobal(pos))


class ProcessMonitor(QThread):
    """应用程序进程资源监控线程"""
    update_signal = pyqtSignal(float, float)  # 发送CPU和内存使用率的信号

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.current_process = psutil.Process(os.getpid())

    def run(self):
        """线程运行函数"""
        while self._is_running:
            try:
                cpu_percent = self.current_process.cpu_percent(interval=1.0)
                memory_info = self.current_process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                self.update_signal.emit(cpu_percent, memory_mb)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._is_running = False
            except Exception as e:
                print(f"监控进程资源时出错: {e}")
            self.msleep(2000)

    def stop(self):
        """停止线程"""
        self._is_running = False
        self.quit()
        self.wait()


class SettingsWindow(QWidget):
    def __init__(self, auto_start_video=None, auto_loop=True):
        super().__init__()
        self.setWindowTitle("LiangYuPaper")
        self.setFixedSize(550, 450)

        self.settings = QSettings("VideoWallpaper", "Settings")
        self.wallpaper_window = None

        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_plugins()

        self.init_ui()
        self.init_tray_icon()

        self.load_settings()

        self.system_monitor = ProcessMonitor()
        self.system_monitor.update_signal.connect(self.update_system_status)
        self.system_monitor.start()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_autostart_status)
        self.status_timer.start(2000)

        if auto_start_video:
            self.path_input.setText(auto_start_video)
            self.loop_check.setChecked(auto_loop)
            QTimer.singleShot(100, self.start_wallpaper)

    def hide(self):
        """隐藏窗口，但不影响托盘菜单"""
        super().hide()
        # 确保托盘图标仍然有效
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "已最小化",
                "程序已最小化到系统托盘",
                QSystemTrayIcon.Information,
                2000
            )

    def closeEvent(self, event):
        # 如果启用了"最小化到托盘"且不是通过托盘菜单退出，则最小化到托盘
        if self.minimize_to_tray_check.isChecked() and self.tray_icon.isVisible():
            self.hide()
            event.ignore()  # 忽略关闭事件
            return

        # 询问是否真的关闭程序
        reply = QMessageBox.question(
            self,
            "确认关闭",
            "确定要退出程序吗？\n当前运行的壁纸也将停止。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # 默认选项
        )

        if reply == QMessageBox.Yes:
            # 停止壁纸并清理资源
            if self.wallpaper_window:
                self.stop_wallpaper()

            # 停止系统监控线程
            self.system_monitor.stop()

            # 隐藏托盘图标
            self.tray_icon.hide()

            event.accept()  # 接受关闭事件
        else:
            event.ignore()  # 忽略关闭事件
    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Video Path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("视频路径:"))
        self.path_input = QLineEdit()
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_video)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        main_layout.addLayout(path_layout)

        # Options
        options_layout = QHBoxLayout()
        self.loop_check = QCheckBox("循环播放")
        self.loop_check.setChecked(True)
        self.minimize_to_tray_check = QCheckBox("X键最小化到托盘")
        self.minimize_to_tray_check.setChecked(True)
        options_layout.addWidget(self.loop_check)
        options_layout.addWidget(self.minimize_to_tray_check)
        options_layout.addStretch()
        main_layout.addLayout(options_layout)

        # Autostart
        autostart_group = QWidget()
        autostart_layout_main = QVBoxLayout(autostart_group)
        autostart_group.setStyleSheet(
            "QWidget { border: 1px solid #ccc; border-radius: 5px; } QLabel { border: none; }")

        bat_layout = QHBoxLayout()
        bat_layout.addWidget(QLabel("启动脚本 (BAT):"))
        self.bat_input = QLineEdit()
        self.browse_bat_btn = QPushButton("选择...")
        self.browse_bat_btn.clicked.connect(self.browse_bat_file)
        self.create_bat_btn = QPushButton("创建...")
        self.create_bat_btn.clicked.connect(self.create_bat_file)
        bat_layout.addWidget(self.bat_input)
        bat_layout.addWidget(self.browse_bat_btn)
        bat_layout.addWidget(self.create_bat_btn)
        autostart_layout_main.addLayout(bat_layout)

        self.autostart_status_label = QLabel("自启动状态: 检查中...")
        autostart_layout_main.addWidget(self.autostart_status_label)

        autostart_btn_layout = QHBoxLayout()
        self.set_autostart_btn = QPushButton("设置为自启动")
        self.set_autostart_btn.clicked.connect(self.set_autostart)
        self.unset_autostart_btn = QPushButton("取消自启动")
        self.unset_autostart_btn.clicked.connect(self.unset_autostart)
        autostart_btn_layout.addWidget(self.set_autostart_btn)
        autostart_btn_layout.addWidget(self.unset_autostart_btn)
        autostart_layout_main.addLayout(autostart_btn_layout)

        main_layout.addWidget(autostart_group)

        # Plugin Management
        plugin_group = QWidget()
        plugin_layout = QVBoxLayout(plugin_group)
        plugin_group.setStyleSheet("QWidget { border: 1px solid #ccc; border-radius: 5px; }")

        plugin_btn_layout = QHBoxLayout()
        self.plugin_info_btn = QPushButton("插件管理")
        self.plugin_info_btn.clicked.connect(self.show_plugin_info)
        self.reload_plugins_btn = QPushButton("重新加载插件")
        self.reload_plugins_btn.clicked.connect(self.reload_plugins)
        self.open_plugin_dir_btn = QPushButton("打开插件目录")
        plugin_btn_layout.addWidget(self.plugin_info_btn)
        plugin_btn_layout.addWidget(self.reload_plugins_btn)
        plugin_btn_layout.addWidget(self.open_plugin_dir_btn)
        plugin_layout.addLayout(plugin_btn_layout)

        main_layout.addWidget(plugin_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存设置")
        self.save_btn.clicked.connect(self.save_settings)
        self.start_btn = QPushButton("启动壁纸")
        self.start_btn.clicked.connect(self.start_wallpaper)
        self.stop_btn = QPushButton("停止壁纸")
        self.stop_btn.clicked.connect(self.stop_wallpaper)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv);;所有文件 (*.*)"
        )
        if file_path:
            self.path_input.setText(file_path)

    def browse_bat_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择BAT文件", "",
            "批处理文件 (*.bat);;所有文件 (*.*)"
        )
        if file_path:
            self.bat_input.setText(file_path)

    def load_settings(self):
        video_path = self.settings.value("video_path", "")
        loop = self.settings.value("loop", True, type=bool)
        bat_path = self.settings.value("bat_path", "")
        minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)

        self.path_input.setText(video_path)
        self.loop_check.setChecked(loop)
        self.bat_input.setText(bat_path)
        self.minimize_to_tray_check.setChecked(minimize_to_tray)

    def save_settings(self):
        video_path = self.path_input.text().strip()
        loop = self.loop_check.isChecked()
        bat_path = self.bat_input.text().strip()
        minimize_to_tray = self.minimize_to_tray_check.isChecked()

        if not video_path:
            QMessageBox.warning(self, "警告", "请先选择视频文件！")
            return

        if not os.path.exists(video_path):
            QMessageBox.warning(self, "警告", "视频文件不存在，请重新选择！")
            return

        if bat_path and not os.path.exists(bat_path):
            QMessageBox.warning(self, "警告", "所选BAT文件不存在，请重新选择！")
            return

        self.settings.setValue("video_path", video_path)
        self.settings.setValue("loop", loop)
        self.settings.setValue("bat_path", bat_path)
        self.settings.setValue("minimize_to_tray", minimize_to_tray)
        self.settings.sync()

        settings_dict = {
            'video_path': video_path,
            'loop': loop,
            'bat_path': bat_path,
            'minimize_to_tray': minimize_to_tray
        }
        self.plugin_manager.trigger_settings_changed(settings_dict)

        QMessageBox.information(self, "成功", "设置已保存！")

    def start_wallpaper(self):
        video_path = self.path_input.text().strip()
        if not video_path:
            QMessageBox.warning(self, "警告", "请先选择视频文件！")
            return

        if not os.path.exists(video_path):
            QMessageBox.warning(self, "警告", "视频文件不存在，请重新选择！")
            return

        if self.wallpaper_window:
            self.stop_wallpaper()

        try:
            loop = self.loop_check.isChecked()
            self.plugin_manager.trigger_wallpaper_start(video_path, loop)
            self.wallpaper_window = VideoWallpaper(video_path, loop, self.plugin_manager)
            self.wallpaper_window.show()

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            QMessageBox.information(self, "成功", "视频壁纸已启动！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动壁纸时发生错误:\n{str(e)}")

    def stop_wallpaper(self):
        if self.wallpaper_window:
            try:
                success = self.wallpaper_window.stop_wallpaper()

                if success:
                    self.wallpaper_window.deleteLater()
                    self.wallpaper_window = None
                    self.plugin_manager.trigger_wallpaper_stop()
                    self.start_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)

                    QMessageBox.information(self, "成功", "视频壁纸已停止！")
                else:
                    QMessageBox.warning(self, "警告", "停止壁纸时遇到一些问题，但已尝试清理资源。")
                    self.wallpaper_window = None
                    self.start_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"停止壁纸时发生错误: {str(e)}")
                self.wallpaper_window = None
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)

    def create_bat_file(self):
        video_path = self.path_input.text().strip()
        if not video_path:
            QMessageBox.warning(self, "警告", "请先选择视频文件！")
            return

        if not os.path.exists(video_path):
            QMessageBox.warning(self, "警告", "视频文件不存在，请重新选择！")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存启动脚本", "", "批处理文件 (*.bat)"
        )

        if not save_path:
            return

        python_exe = sys.executable
        script_path = os.path.abspath(__file__)

        content = f'''@echo off
:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 需要管理员权限，正在重新启动...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"{save_path}\"' -Verb RunAs"
    exit /b
)

echo 正在启动视频壁纸...
"{python_exe}" "{script_path}" --gui-with-video "{video_path}"

echo 执行完成，创建标记文件...
echo completed > "{os.path.dirname(save_path)}\\demotest"

pause
'''

        try:
            with open(save_path, 'w', encoding='gbk') as f:
                f.write(content)
            QMessageBox.information(self, "成功", f"启动脚本已创建：\n{save_path}")
            self.bat_input.setText(save_path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"创建脚本失败: {str(e)}")


    def set_autostart(self):
        bat_path = self.bat_input.text().strip().replace("/","\\")
        if not bat_path:
            QMessageBox.warning(self, "警告", "请先选择要设置自启动的BAT文件！")
            return

        if not os.path.exists(bat_path):
            QMessageBox.warning(self, "警告", "所选BAT文件不存在，请重新选择！")
            return

        try :
            auto_start = AutoStartUtil("LiangYuPaper", bat_path)
            auto_start.set_autostart()
            QMessageBox.information(self, "成功", "自启动已设置！")
            self.update_autostart_status()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置自启动时发生错误:\n{str(e)}")

    def unset_autostart(self):
        try:

            auto_start = AutoStartUtil("LiangYuPaper")
            auto_start.unset_autostart()
            QMessageBox.information(self, "成功", "自启动已取消！")
            self.update_autostart_status()
        except FileNotFoundError:
            QMessageBox.information(self, "提示", "自启动尚未设置。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"取消自启动时发生错误:\n{str(e)}")

    def update_autostart_status(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run")

            try:
                value, _ = winreg.QueryValueEx(key, "LiangYuPaper")
                self.autostart_status_label.setText(f"自启动状态: 已启用\n路径: {value}")
                self.autostart_status_label.setStyleSheet("color: green;")
            except FileNotFoundError:
                self.autostart_status_label.setText("自启动状态: 未启用")
                self.autostart_status_label.setStyleSheet("color: red;")
            winreg.CloseKey(key)
        except Exception as e:
            print(f"检查自启动状态时出错: {e}")

    def show_normal(self):
        """显示窗口并确保它不在最小化状态"""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
    def init_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(self, "系统托盘", "系统托盘不可用")
            return

        # 确保托盘图标有有效的图标
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_MediaPlay)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("视频壁纸")

        # 创建托盘菜单
        tray_menu = QMenu()

        # 添加菜单项
        show_action = QAction("显示设置窗口", self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)

        hide_action = QAction("隐藏设置窗口", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        start_action = QAction("启动壁纸", self)
        start_action.triggered.connect(self.start_wallpaper)
        tray_menu.addAction(start_action)

        stop_action = QAction("停止壁纸", self)
        stop_action.triggered.connect(self.stop_wallpaper)
        tray_menu.addAction(stop_action)

        tray_menu.addSeparator()

        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        # 设置上下文菜单
        self.tray_icon.setContextMenu(tray_menu)

        # 连接激活信号
        self.tray_icon.activated.connect(self.on_tray_activated)

        # 显示托盘图标
        self.tray_icon.show()
    # 新增：托盘图标激活事件处理
    def on_tray_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.Trigger:  # 单击
            pass
        elif reason == QSystemTrayIcon.DoubleClick:  # 双击
            self.show_normal()
        elif reason == QSystemTrayIcon.Context:  # 右键菜单
            pass  # 已经由上下文菜单处理

    def quit_application(self):
        reply = QMessageBox.question(
            self,
            "确认关闭",
            "确定要退出程序吗？\n当前运行的壁纸也将停止。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # 默认选项
        )

        if reply == QMessageBox.Yes:
            # 停止壁纸并清理资源
            if self.wallpaper_window:
                self.stop_wallpaper()

            # 停止系统监控线程
            self.system_monitor.stop()

            # 隐藏托盘图标
            self.tray_icon.hide()

            # 退出应用程序
            QApplication.quit()




    def show_plugin_info(self):
        dialog = PluginInfoDialog(self.plugin_manager, self)
        dialog.exec_()

    def reload_plugins(self):
        try:
            self.plugin_manager.load_plugins()
            plugin_count = len(self.plugin_manager.plugins)
            QMessageBox.information(self, "插件重载", f"成功加载 {plugin_count} 个插件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"重新加载插件时发生错误:\n{str(e)}")

    def open_plugin_directory(self):
        try:
            plugin_dir = self.plugin_manager.plugin_dir
            if os.path.exists(plugin_dir):
                os.startfile(plugin_dir)
            else:
                QMessageBox.warning(self, "警告", "插件目录不存在")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开插件目录时发生错误:\n{str(e)}")

    def update_system_status(self, cpu_percent, memory_mb):
        title = f"LiangYuPaper - CPU: {cpu_percent:.1f}% | 内存: {memory_mb:.1f}MB"
        self.setWindowTitle(title)


def main():
    app = QApplication(sys.argv)

    # 检查命令行参数
    if len(sys.argv) > 2 and sys.argv[1] == "--gui-with-video":
        # 命令行指定视频文件，但显示GUI界面
        video_path = sys.argv[2]
        loop = True

        # 检查是否有额外的循环参数
        if len(sys.argv) > 3 and sys.argv[3] == "--no-loop":
            loop = False

        # 创建设置窗口并自动启动视频
        window = SettingsWindow(auto_start_video=video_path, auto_loop=loop)
        window.show()
        sys.exit(app.exec_())
    elif len(sys.argv) > 1 and sys.argv[1] == "--autostart":
        # 自动启动模式，从设置中加载参数，显示GUI
        settings = QSettings("VideoWallpaper", "Settings")
        video_path = settings.value("video_path", "")
        loop = settings.value("loop", True, type=bool)

        if video_path and os.path.exists(video_path):
            # 创建设置窗口并自动启动视频
            window = SettingsWindow(auto_start_video=video_path, auto_loop=loop)
            window.show()
            sys.exit(app.exec_())
        else:
            # 如果没有设置或文件不存在，仍然显示GUI
            window = SettingsWindow()
            window.show()
            QMessageBox.warning(window, "警告", "自动启动失败：未找到有效的视频文件设置。")
            sys.exit(app.exec_())
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        video_path = sys.argv[1]
        loop = True

        # 检查是否有额外的循环参数
        if len(sys.argv) > 2 and sys.argv[2] == "--no-loop":
            loop = False

        # 创建设置窗口并自动启动视频
        window = SettingsWindow(auto_start_video=video_path, auto_loop=loop)
        window.show()
        sys.exit(app.exec_())
    else:
        # 显示设置窗口
        window = SettingsWindow()
        window.show()
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
