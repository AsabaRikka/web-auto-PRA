from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QTextEdit, QStatusBar)
from PySide6.QtCore import Qt, Signal, QObject
from core.browser import BrowserManager
from core.recorder import Recorder
from core.player import Player
import asyncio

class AppSignals(QObject):
    recorded = Signal(dict)
    play_status = Signal(int, str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebAuto Recorder - 网页自动化录制工具")
        self.resize(1000, 700)

        self.recorded_steps = []
        self.browser_manager = BrowserManager()
        self.signals = AppSignals()
        self.signals.recorded.connect(self.add_step_to_ui)
        self.signals.play_status.connect(self.update_step_status)
        
        self.recorder = Recorder(self.browser_manager, self.on_step_recorded)
        self.player = Player(self.browser_manager, self.on_play_status_change)

        # 主界面布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧面板：操作步骤列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.step_label = QLabel("操作步骤记录")
        self.step_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.step_list = QListWidget()
        
        left_layout.addWidget(self.step_label)
        left_layout.addWidget(self.step_list)

        # 右侧面板：控制与日志
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 控制按钮
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setFixedHeight(40)
        self.record_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        self.play_btn = QPushButton("回放流程")
        self.play_btn.setFixedHeight(40)
        self.play_btn.setEnabled(False)

        # 日志区域
        self.log_label = QLabel("执行日志")
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        right_layout.addWidget(self.record_btn)
        right_layout.addWidget(self.play_btn)
        right_layout.addWidget(self.log_label)
        right_layout.addWidget(self.log_area)

        # 将左右面板加入主布局
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 信号连接
        self.record_btn.clicked.connect(self.toggle_recording)
        self.play_btn.clicked.connect(self.start_playback)

    def on_step_recorded(self, step_data):
        self.recorded_steps.append(step_data)
        self.signals.recorded.emit(step_data)

    def add_step_to_ui(self, step_data):
        item_text = f"[{step_data['type'].upper()}] {step_data['description']}"
        self.step_list.addItem(item_text)
        self.log_area.append(f"记录步骤: {item_text}")

    def on_play_status_change(self, index, status):
        self.signals.play_status.emit(index, status)

    def update_step_status(self, index, status):
        item = self.step_list.item(index)
        if item:
            original_text = item.text().split(" | ")[0]
            item.setText(f"{original_text} | 状态: {status}")
            if "success" in status:
                item.setForeground(Qt.green)
            elif "failed" in status:
                item.setForeground(Qt.red)
            self.log_area.append(f"步骤 {index + 1}: {status}")

    def toggle_recording(self):
        if self.record_btn.text() == "开始录制":
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.recorded_steps = []
        self.step_list.clear()
        self.record_btn.setText("停止录制")
        self.record_btn.setStyleSheet("background-color: #9e9e9e; color: white;")
        self.status_bar.showMessage("正在初始化浏览器...")
        
        try:
            self.browser_manager.start_sync()
            self.browser_manager.run_coroutine(self.recorder.start())
            self.browser_manager.run_coroutine(self.browser_manager.page.goto("https://www.baidu.com"))
            self.status_bar.showMessage("正在录制中...")
        except Exception as e:
            self.log_area.append(f"启动失败: {str(e)}")
            self.stop_recording()

    def stop_recording(self):
        self.recorder.stop()
        self.record_btn.setText("开始录制")
        self.record_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.status_bar.showMessage("录制已停止")
        self.play_btn.setEnabled(len(self.recorded_steps) > 0)

    def start_playback(self):
        self.status_bar.showMessage("开始回放...")
        self.log_area.append("--- 开始回放流程 ---")
        self.browser_manager.run_coroutine(self.player.play(self.recorded_steps))

    def closeEvent(self, event):
        self.browser_manager.run_coroutine(self.browser_manager.close())
        event.accept()
