# 原神自动攻略助手 / Genshin Auto-Guide Helper

一个通过 AI 分析攻略视频，自动执行游戏操作的 Windows 应用程序。

## 功能特点

- 📹 **视频分析**: 导入攻略视频，AI 自动提取操作步骤
- 🤖 **AI 驱动**: 使用 GPT-4 Vision 理解视频内容和游戏画面
- 🎮 **自动执行**: 自动控制游戏进行宝箱、神瞳收集
- 🔄 **智能恢复**: 异常情况下使用 AI 进行决策恢复
- 🎨 **现代界面**: 暗色主题，直观易用

## 系统要求

- Windows 10/11 (64位)
- Python 3.10 或更高版本
- 原神 PC 客户端
- OpenAI API Key (需要 GPT-4 Vision 权限)

## 安装

### 方法 1: 从源码运行

```bash
# 克隆或下载项目
cd gihelper

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

### 方法 2: 使用可执行文件

```bash
# 打包成可执行文件
python build.py

# 运行 dist/GenshinAutoGuide.exe
```

## 使用说明

### 1. 配置 API

1. 打开程序后，点击 **设置** → **首选项**
2. 在 **API 设置** 标签页输入你的 OpenAI API Key
3. 点击 **测试 API 连接** 确认配置正确
4. 点击 **保存**

### 2. 导入攻略视频

1. 点击 **打开视频** 或拖放视频文件到窗口
2. 支持的格式: MP4, AVI, MKV, MOV, WMV

### 3. 分析视频

1. 点击工具栏的 **分析视频** 按钮
2. 等待 AI 分析完成（可能需要几分钟）
3. 分析完成后会显示提取的步骤数量

### 4. 执行攻略

1. 确保原神游戏已打开，角色在正确的起始位置
2. 点击 **开始执行** 按钮
3. 程序会自动控制游戏执行攻略

### 5. 紧急停止

- 按 **F12** 立即停止所有操作
- 按 **F11** 暂停/继续执行
- 将鼠标移到屏幕角落也可触发安全停止

## 项目结构

```
gihelper/
├── main.py              # 应用入口
├── config.py            # 配置管理
├── requirements.txt     # 依赖列表
├── build.py            # 打包脚本
├── ui/                  # GUI 模块
│   ├── main_window.py   # 主窗口
│   ├── video_panel.py   # 视频面板
│   ├── control_panel.py # 控制面板
│   └── settings_dialog.py # 设置对话框
├── video/               # 视频分析模块
│   ├── extractor.py     # 帧提取
│   └── analyzer.py      # AI 分析
├── screen/              # 屏幕识别模块
│   ├── capture.py       # 截图
│   └── detector.py      # 检测
├── automation/          # 自动化模块
│   ├── controller.py    # 控制器
│   └── navigator.py     # 导航
└── engine/              # 决策引擎
    └── decision.py      # AI 决策
```

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI | PyQt6 |
| 视频处理 | OpenCV |
| AI 接口 | OpenAI GPT-4 Vision |
| 屏幕捕获 | mss |
| 自动化 | pyautogui / pydirectinput |

## 注意事项

1. **API 费用**: GPT-4 Vision 调用会产生费用，请监控你的使用量
2. **网络要求**: 需要稳定的网络连接访问 OpenAI API

## 故障排除

### 程序启动失败
- 确保 Python 版本 >= 3.10
- 确保所有依赖已正确安装

### API 连接失败
- 检查 API Key 是否正确
- 检查网络连接
- 如果在中国大陆，可能需要代理

### 无法检测游戏窗口
- 确保游戏以窗口模式运行
- 确保游戏窗口标题包含"原神"

### 操作不准确
- 调整设置中的操作延迟
- 确保游戏分辨率与设置一致
