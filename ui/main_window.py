from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QTextEdit, QStatusBar, QLineEdit)
from PySide6.QtCore import Qt, Signal, QObject
from core.browser import BrowserManager
from core.recorder import Recorder
from core.player import Player
import asyncio

class AppSignals(QObject):
    recorded = Signal(dict)
    play_status = Signal(int, str)
    similar_found = Signal(list)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebAuto Recorder - 网页自动化录制工具")
        self.resize(1200, 800)

        self.recorded_steps = []
        self.browser_manager = BrowserManager()
        self.signals = AppSignals()
        self.signals.recorded.connect(self.add_step_to_ui)
        self.signals.play_status.connect(self.update_step_status)
        self.signals.similar_found.connect(self.display_similar_elements)
        
        self.recorder = Recorder(self.browser_manager, self.on_step_recorded)
        self.player = Player(self.browser_manager, self.on_play_status_change)

        # 主界面布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 左侧面板：操作步骤与相似元素 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 操作步骤部分
        self.step_label = QLabel("1. 操作步骤记录")
        self.step_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        self.step_list = QListWidget()
        
        # 相似元素部分
        self.similar_label = QLabel("2. 发现的相似元素")
        self.similar_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin-top: 10px;")
        self.similar_list = QListWidget()
        
        left_layout.addWidget(self.step_label)
        left_layout.addWidget(self.step_list, 3) # 比例 3
        left_layout.addWidget(self.similar_label)
        left_layout.addWidget(self.similar_list, 2) # 比例 2

        # --- 右侧面板：控制与日志 ---
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

        # 核心控制按钮
        control_layout = QHBoxLayout()
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setFixedHeight(40)
        self.record_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        self.search_similar_btn = QPushButton("搜索相似元素")
        self.search_similar_btn.setFixedHeight(40)
        self.search_similar_btn.setEnabled(False)
        self.search_similar_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")

        self.play_btn = QPushButton("回放流程")
        self.play_btn.setFixedHeight(40)
        self.play_btn.setEnabled(False)
        
        control_layout.addWidget(self.record_btn)
        control_layout.addWidget(self.search_similar_btn)
        control_layout.addWidget(self.play_btn)

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
        self.search_similar_btn.clicked.connect(self.search_similar)
        self.step_list.itemClicked.connect(self.on_step_selected)

    def on_step_selected(self):
        """当步骤被选中时，启用搜索相似按钮"""
        self.search_similar_btn.setEnabled(True)

    def search_similar(self):
        """搜索与选中步骤相似的元素"""
        current_row = self.step_list.currentRow()
        if current_row < 0:
            return
            
        selected_step = self.recorded_steps[current_row]
        xpath = selected_step.get('xpath')
        if not xpath:
            self.log_area.append("选中步骤没有有效的 XPath。")
            return
            
        self.log_area.append(f"正在搜索与 {xpath} 相似的元素...")
        self.status_bar.showMessage("搜索相似元素中...")
        
        async def run_search():
            results = await self.browser_manager.find_similar_elements(xpath)
            self.signals.similar_found.emit(results)
            
        self.browser_manager.run_coroutine(run_search())

    def display_similar_elements(self, results):
        """显示搜索到的相似元素"""
        self.similar_list.clear()
        if not results:
            self.log_area.append("未发现相似元素。")
            self.status_bar.showMessage("未发现相似元素")
            return
            
        for el in results:
            text = f"[{el['tagName']}] {el['innerText']} | XPath: {el['xpath']}"
            self.similar_list.addItem(text)
            
        self.log_area.append(f"发现 {len(results)} 个相似元素。")
        self.status_bar.showMessage(f"发现 {len(results)} 个相似元素")

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
