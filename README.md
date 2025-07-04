# LiangYuPaperMaster 项目说明

## 项目概述
LiangYuPaperMaster 是一个基于 Python 的桌面壁纸管理项目，借助 PyQt5 和 VLC 实现视频壁纸功能，同时支持插件扩展，可在壁纸上方添加自定义控件和图形。

## 项目结构
```
├── README.md
├── Utils/
│   ├── AutoStartUtil.py          # Windows 自启动工具类
│   └── __pycache__/
├── env_setup.bat                 # 环境搭建脚本
├── launch.bat                    # 项目启动脚本
├── main.py                       # 项目主程序，包含插件管理器和壁纸设置功能
├── plugin_base.py                # 插件基类，定义插件开发规范
├── plugins/
│   └── exampleplugin.py          # 示例插件，可在桌面上绘制简单图形和文字
└── requirements.txt              # 项目依赖文件
```

## 环境搭建
1. 确保已安装 Python 环境。
2. 运行以下命令搭建虚拟环境并安装依赖：
```powershell
.\env_setup.bat
```

## 项目启动
运行以下命令激活虚拟环境并启动项目：
```powershell
.\launch.bat
```

## 核心功能
### 视频壁纸功能
使用 VLC 播放器实现视频壁纸功能，支持循环播放，并可设置为桌面壁纸。
### 插件系统
- **插件管理器**：位于 `main.py`，负责加载、触发事件和清理插件。
- **插件基类**：`plugin_base.py` 定义了插件开发的基本规范和接口。
- **示例插件**：`plugins/exampleplugin.py` 展示了如何在壁纸上方绘制简单图形和文字，支持设置修改和用户互动。
### 自启动功能
`Utils/AutoStartUtil.py` 提供了 Windows 系统下的自启动工具类，可设置或取消程序自启动。

## 插件开发
若要开发新插件，需遵循以下步骤：
1. 在 `plugins` 目录下创建新的 Python 文件。
2. 继承 `PluginBase` 类并实现所有抽象方法。
3. 实现 `create_plugin` 函数，返回插件实例。

## 项目依赖
项目依赖记录在 `requirements.txt` 文件中，具体如下：
```plaintext
PyQt5==5.15.9
requests==2.31.0
pyautogui==0.9.54
keyboard==0.13.5
python-dotenv==1.0.0
```

## 注意事项
- 运行项目需要安装 VLC 播放器，因为项目使用 VLC 实现视频播放功能。
- 设置自启动功能需要管理员权限。
- 你或许可以在这下载VLC https://download.videolan.org/pub/videolan/vlc/last/win64/