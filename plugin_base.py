from abc import ABC, abstractmethod
from PyQt5.QtWidgets import QWidget

class PluginBase(ABC):
    """插件基类，所有插件必须继承此类"""

    def __init__(self):
        self.name = "Unknown Plugin"
        self.version = "1.0.0"
        self.description = "No description"
        self.author = "Unknown"
        self.enabled = True

    @abstractmethod
    def initialize(self, app_instance):
        """
        插件初始化方法，app_instance是主应用实例
        无论如何 浏览插件 启用与否 都会触发初始化函数
        """
        pass

    @abstractmethod
    def on_wallpaper_start(self, video_path, loop):
        """壁纸启动时触发"""
        pass

    @abstractmethod
    def on_wallpaper_stop(self):
        """壁纸停止时触发"""
        pass

    def on_settings_changed(self, settings):
        """设置更改时触发（可选实现）"""
        pass

    def cleanup(self):
        """清理资源（可选实现）"""
        pass

    @abstractmethod
    def show_settings_dialog(self):
        """显示插件的设置对话框"""
        pass

    @abstractmethod
    def operate_on_window(self, window: QWidget):
        """
        在窗口上进行操作
        :param window: VideoWallpaper窗口实例，可以添加自定义控件
        """
        pass