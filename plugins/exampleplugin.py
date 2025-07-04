import traceback
from PyQt5.QtWidgets import QWidget,QPushButton
from PyQt5.QtCore import Qt,QSettings
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
import tkinter as tk
from tkinter import messagebox
import os

from plugin_base import PluginBase


class CustomWidgetPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.name = "简单图形插件"
        self.version = "1.0.0"
        self.description = "在桌面上绘制简单的图形和文字"
        self.author = "LiangYuPaper"
        self.settings = {
            'text': 'Hello World!',
            'color': '#FFFFFF',
            'position_x': 100,
            'position_y': 100
        }
        self.widget = None

    def initialize(self, app_instance):
        print(f"[{self.name}] 插件初始化")
        self.app = app_instance
        
        # 从QSettings加载保存的设置
        settings = QSettings("VideoWallpaper", "PluginSettings")
        settings.beginGroup(f"plugins/{self.name}")
        
        # 加载每个设置，如果不存在则使用默认值
        self.settings['text'] = settings.value('text', self.settings['text'], type=str)
        self.settings['color'] = settings.value('color', self.settings['color'], type=str)
        self.settings['position_x'] = settings.value('position_x', self.settings['position_x'], type=int)
        self.settings['position_y'] = settings.value('position_y', self.settings['position_y'], type=int)
        
        settings.endGroup()

    def on_wallpaper_start(self, video_path, loop):
        print(f"[{self.name}] 壁纸启动: {os.path.basename(video_path)}")

    def on_wallpaper_stop(self):
        print(f"[{self.name}] 壁纸停止")
        if self.widget:
            self.widget.close()
            self.widget = None

    def on_settings_changed(self, settings):
        print(f"[{self.name}] 设置已更改")

    def show_settings_dialog(self):
        root = tk.Tk()
        root.title(f"{self.name} 设置")

        tk.Label(root, text="显示文本:").pack(pady=5)
        text_entry = tk.Entry(root)
        text_entry.insert(0, self.settings.get('text', 'Hello World!'))
        text_entry.pack(pady=5)

        tk.Label(root, text="文本颜色(十六进制):").pack(pady=5)
        color_entry = tk.Entry(root)
        color_entry.insert(0, self.settings.get('color', '#FFFFFF'))
        color_entry.pack(pady=5)

        tk.Label(root, text="X位置:").pack(pady=5)
        x_entry = tk.Entry(root)
        x_entry.insert(0, str(self.settings.get('position_x', 100)))
        x_entry.pack(pady=5)

        tk.Label(root, text="Y位置:").pack(pady=5)
        y_entry = tk.Entry(root)
        y_entry.insert(0, str(self.settings.get('position_y', 100)))
        y_entry.pack(pady=5)

        def save_settings():
            new_settings = {
                'text': text_entry.get(),
                'color': color_entry.get(),
                'position_x': int(x_entry.get()),
                'position_y': int(y_entry.get())
            }
            # 保存设置到QSettings
            settings = QSettings("VideoWallpaper", "PluginSettings")
            settings.beginGroup(f"plugins/{self.name}")
            for key, value in new_settings.items():
                settings.setValue(key, value)
            settings.endGroup()
            self.settings.update(new_settings)

            if self.widget:
                self.widget.move(self.settings['position_x'], self.settings['position_y'])
                self.widget.update()  # 强制重绘

            messagebox.showinfo("保存成功", "设置已保存")
            root.destroy()

        save_button = tk.Button(root, text="保存设置", command=save_settings)
        save_button.pack(pady=20)

        root.mainloop()

    def operate_on_window(self, window):
        """在壁纸上方的透明覆盖层上绘制简单图形"""
        try:
            # 创建自定义控件
            self.widget = QWidget(window)
            self.widget.setGeometry(
                self.settings['position_x'],
                self.settings['position_y'],
                200,
                250
            )

            # 添加互动按钮
            self.button = QPushButton('点击互动', self.widget)
            self.button.setGeometry(50, 180, 100, 30)
            self.button.setStyleSheet("background-color: #4CAF50; color: white;")
            self.button.clicked.connect(self.show_interaction)

            # 设置透明背景
            self.widget.setAttribute(Qt.WA_TranslucentBackground, True)
            self.widget.setStyleSheet("background: transparent;")

            # 重写paintEvent来绘制内容
            def paintEvent(event):
                painter = QPainter(self.widget)
                painter.setRenderHint(QPainter.Antialiasing)

                # 绘制Hello World文本
                painter.setPen(QColor(self.settings['color']))
                font = QFont()
                font.setPointSize(16)
                painter.setFont(font)
                painter.drawText(10, 30, self.settings['text'])

                # 绘制矩形
                painter.setPen(QPen(QColor(255, 0, 0), 2))  # 红色边框
                painter.setBrush(QBrush(QColor(255, 0, 0, 100)))  # 半透明红色填充
                painter.drawRect(50, 50, 100, 60)

                # 绘制圆形
                painter.setPen(QPen(QColor(0, 0, 255), 2))  # 蓝色边框
                painter.setBrush(QBrush(QColor(0, 0, 255, 100)))  # 半透明蓝色填充
                painter.drawEllipse(70, 120, 60, 60)

                painter.end()

            self.widget.paintEvent = paintEvent

            # 显示控件
            self.widget.show()
            print(f"[{self.name}] 简单图形已绘制到壁纸覆盖层")
        except Exception as e:
            print(f"[{self.name}] 绘制图形时出错: {e}")
            traceback.print_exc()

    def show_interaction(self):
        tk.messagebox.showinfo("互动", "您点击了插件按钮！")

    def close_widget(self):
        """关闭控件的方法"""
        if self.widget:
            self.widget.close()
            self.widget = None
            print(f"[{self.name}] 控件已关闭")


def create_plugin():
    return CustomWidgetPlugin()