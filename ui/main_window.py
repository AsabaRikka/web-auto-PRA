from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QTextEdit, QStatusBar, QLineEdit, QSpinBox)
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
        self.resize(1000, 750)

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

        # 网站访问控制
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit("https://www.baidu.com")
        self.open_url_btn = QPushButton("访问网站")
        self.save_session_btn = QPushButton("保存登录状态")
        url_layout.addWidget(QLabel("网站地址:"))
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.open_url_btn)
        url_layout.addWidget(self.save_session_btn)

        # 录制与回放控制
        control_layout = QHBoxLayout()
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setFixedHeight(40)
        self.record_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        self.play_btn = QPushButton("回放流程")
        self.play_btn.setFixedHeight(40)
        self.play_btn.setEnabled(False)

        self.batch_count_spin = QSpinBox()
        self.batch_count_spin.setRange(1, 1000)
        self.batch_count_spin.setValue(10)
        self.batch_count_spin.setFixedHeight(40)
        self.batch_count_spin.setPrefix("数量: ")

        self.batch_btn = QPushButton("批量取消收藏")
        self.batch_btn.setFixedHeight(40)
        self.batch_btn.setEnabled(False)
        self.batch_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")

        control_layout.addWidget(self.record_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.batch_count_spin)
        control_layout.addWidget(self.batch_btn)

        # 日志区域
        self.log_label = QLabel("执行日志")
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        right_layout.addLayout(url_layout)
        right_layout.addLayout(control_layout)
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
        self.open_url_btn.clicked.connect(self.open_url)
        self.save_session_btn.clicked.connect(self.save_session)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.play_btn.clicked.connect(self.start_playback)
        self.batch_btn.clicked.connect(self.start_batch_action)

    def start_batch_action(self):
        if not self.recorded_steps:
            self.log_area.append("错误: 请先录制一次点击收藏图标的操作。")
            return
        
        # 寻找第一个点击操作
        click_step = next((s for s in self.recorded_steps if s['type'] == 'click'), None)
        if not click_step:
            self.log_area.append("错误: 录制列表中没有点击操作。")
            return
            
        count = self.batch_count_spin.value()
        self.status_bar.showMessage(f"开始批量操作 (数量: {count})...")
        self.log_area.append(f"--- 开始批量执行: {click_step['tagName']}, 限制数量: {count} ---")
        self.browser_manager.run_coroutine(self.player.play_batch(click_step, max_count=count))

    def open_url(self):
        url = self.url_input.text()
        self.log_area.append(f"正在访问: {url}")
        self.status_bar.showMessage(f"正在访问: {url}")
        try:
            self.browser_manager.start_sync()
            self.browser_manager.run_coroutine(self.browser_manager.goto(url))
        except Exception as e:
            self.log_area.append(f"访问失败: {str(e)}")

    def save_session(self):
        self.log_area.append("正在保存登录状态...")
        try:
            future = self.browser_manager.run_coroutine(self.browser_manager.save_session())
            if future.result():
                self.log_area.append("登录状态保存成功！下次启动将自动加载。")
                self.status_bar.showMessage("登录状态已保存")
            else:
                self.log_area.append("保存失败：浏览器未启动。")
        except Exception as e:
            self.log_area.append(f"保存失败: {str(e)}")

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
        self.status_bar.showMessage("正在初始化录制环境...")
        
        try:
            # 确保浏览器已启动
            self.browser_manager.start_sync()
            # 启动录制脚本注入
            self.browser_manager.run_coroutine(self.recorder.start())
            self.status_bar.showMessage("正在录制中...")
            self.log_area.append("--- 开始录制 ---")
        except Exception as e:
            self.log_area.append(f"启动录制失败: {str(e)}")
            self.stop_recording()

    def stop_recording(self):
        self.recorder.stop()
        self.record_btn.setText("开始录制")
        self.record_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.status_bar.showMessage("录制已停止")
        self.play_btn.setEnabled(len(self.recorded_steps) > 0)
        self.batch_btn.setEnabled(len(self.recorded_steps) > 0)
        self.log_area.append("--- 录制结束 ---")

    def start_playback(self):
        self.status_bar.showMessage("开始回放...")
        self.log_area.append("--- 开始回放流程 ---")
        try:
            self.browser_manager.start_sync()
            self.browser_manager.run_coroutine(self.player.play(self.recorded_steps))
        except Exception as e:
            self.log_area.append(f"回放启动失败: {str(e)}")

    def closeEvent(self, event):
        self.browser_manager.run_coroutine(self.browser_manager.close())
        event.accept()
