from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QTextEdit, QStatusBar)
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebAuto Recorder - 网页自动化录制工具")
        self.resize(1000, 700)

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
        main_layout.addWidget(left_panel, 1)  # 比例 1
        main_layout.addWidget(right_panel, 1) # 比例 1

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 信号连接
        self.record_btn.clicked.connect(self.toggle_recording)

    def toggle_recording(self):
        if self.record_btn.text() == "开始录制":
            self.record_btn.setText("停止录制")
            self.record_btn.setStyleSheet("background-color: #9e9e9e; color: white;")
            self.status_bar.showMessage("正在录制中...")
            # TODO: 启动 Playwright 录制逻辑
        else:
            self.record_btn.setText("开始录制")
            self.record_btn.setStyleSheet("background-color: #f44336; color: white;")
            self.status_bar.showMessage("录制已停止")
            self.play_btn.setEnabled(True)
