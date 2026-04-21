from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QTextEdit, QStatusBar, QLineEdit, QComboBox, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QObject
from core.browser import BrowserManager
from core.recorder import Recorder
from core.player import Player
import asyncio
import os
import json

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
        self.found_similar_elements = [] # 存储搜索到的相似元素原始数据
        self.browser_manager = BrowserManager()
        self.signals = AppSignals()
        self.signals.recorded.connect(self.add_step_to_ui)
        self.signals.play_status.connect(self.update_step_status)
        self.signals.similar_found.connect(self.display_similar_elements)
        
        self.recorder = Recorder(self.browser_manager, self.on_step_recorded)
        self.player = Player(self.browser_manager, self.on_play_status_change)
        
        self.favorites_file = "storage/favorites.json"

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
        similar_header_layout = QHBoxLayout()
        self.similar_label = QLabel("2. 发现的相似元素")
        self.similar_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin-top: 10px;")
        
        self.select_all_btn = QPushButton("全选")
        self.select_invert_btn = QPushButton("反选")
        self.select_all_btn.setFixedWidth(50)
        self.select_invert_btn.setFixedWidth(50)
        
        similar_header_layout.addWidget(self.similar_label)
        similar_header_layout.addStretch()
        similar_header_layout.addWidget(self.select_all_btn)
        similar_header_layout.addWidget(self.select_invert_btn)
        
        self.similar_list = QListWidget()
        
        left_layout.addWidget(self.step_label)
        left_layout.addWidget(self.step_list, 3) # 比例 3
        left_layout.addLayout(similar_header_layout)
        left_layout.addWidget(self.similar_list, 2) # 比例 2

        # --- 右侧面板：控制与日志 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 网站访问控制
        url_layout = QVBoxLayout()
        
        # 第一行：地址输入和访问
        url_input_layout = QHBoxLayout()
        self.url_input = QLineEdit("https://www.baidu.com")
        self.open_url_btn = QPushButton("访问网站")
        self.save_session_btn = QPushButton("保存登录状态")
        url_input_layout.addWidget(QLabel("网站地址:"))
        url_input_layout.addWidget(self.url_input)
        url_input_layout.addWidget(self.open_url_btn)
        url_input_layout.addWidget(self.save_session_btn)
        
        # 第二行：常用网址
        fav_layout = QHBoxLayout()
        self.fav_combo = QComboBox()
        self.fav_combo.setPlaceholderText("选择常用网址...")
        self.save_fav_btn = QPushButton("添加到常用")
        fav_layout.addWidget(QLabel("常用网址:"))
        fav_layout.addWidget(self.fav_combo, 1)
        fav_layout.addWidget(self.save_fav_btn)
        
        url_layout.addLayout(url_input_layout)
        url_layout.addLayout(fav_layout)

        # 核心控制按钮
        control_layout = QHBoxLayout()
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setFixedHeight(40)
        self.record_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        self.search_similar_btn = QPushButton("搜索相似元素")
        self.search_similar_btn.setFixedHeight(40)
        self.search_similar_btn.setEnabled(False)
        self.search_similar_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")

        self.click_similar_btn = QPushButton("点击选中相似元素")
        self.click_similar_btn.setFixedHeight(40)
        self.click_similar_btn.setEnabled(False)
        self.click_similar_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.play_btn = QPushButton("回放流程")
        self.play_btn.setFixedHeight(40)
        self.play_btn.setEnabled(False)
        
        control_layout.addWidget(self.record_btn)
        control_layout.addWidget(self.search_similar_btn)
        control_layout.addWidget(self.click_similar_btn)
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
        self.save_fav_btn.clicked.connect(self.save_favorite)
        self.fav_combo.currentIndexChanged.connect(self.on_favorite_selected)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.play_btn.clicked.connect(self.start_playback)
        self.search_similar_btn.clicked.connect(self.search_similar)
        self.click_similar_btn.clicked.connect(self.click_selected_similar)
        self.select_all_btn.clicked.connect(self.select_all_similar)
        self.select_invert_btn.clicked.connect(self.select_invert_similar)
        self.step_list.itemClicked.connect(self.on_step_selected)
        self.similar_list.itemClicked.connect(self.on_similar_selected)
        self.similar_list.itemChanged.connect(self.on_similar_item_changed)
        self.similar_list.itemDoubleClicked.connect(self.click_selected_similar)
        
        # 初始化加载常用网址
        self.load_favorites()

    def load_favorites(self):
        """从本地文件加载常用网址"""
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    favorites = json.load(f)
                    self.fav_combo.clear()
                    self.fav_combo.addItems(favorites)
            except Exception as e:
                self.log_area.append(f"加载常用网址失败: {str(e)}")

    def save_favorite(self):
        """保存当前网址到常用列表"""
        url = self.url_input.text().strip()
        if not url:
            return
            
        # 读取现有
        favorites = []
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    favorites = json.load(f)
            except:
                pass
        
        if url not in favorites:
            favorites.append(url)
            try:
                os.makedirs("storage", exist_ok=True)
                with open(self.favorites_file, 'w', encoding='utf-8') as f:
                    json.dump(favorites, f, indent=4, ensure_ascii=False)
                self.load_favorites() # 重新加载界面
                self.log_area.append(f"已添加到常用网址: {url}")
            except Exception as e:
                self.log_area.append(f"保存常用网址失败: {str(e)}")
        else:
            self.log_area.append("该网址已在常用列表中。")

    def on_favorite_selected(self, index):
        """当常用网址被选中时，填入输入框"""
        if index >= 0:
            url = self.fav_combo.itemText(index)
            self.url_input.setText(url)

    def on_step_selected(self):
        """当步骤被选中时，启用搜索相似按钮"""
        self.search_similar_btn.setEnabled(True)

    def on_similar_selected(self):
        """当相似元素被选中时，启用点击按钮"""
        # 如果有任何项被选中或打钩，则启用按钮
        self.update_click_similar_btn_state()

    def on_similar_item_changed(self, item):
        """当相似元素勾选状态改变时"""
        self.update_click_similar_btn_state()

    def update_click_similar_btn_state(self):
        """更新点击相似元素按钮的状态"""
        has_checked = False
        for i in range(self.similar_list.count()):
            if self.similar_list.item(i).checkState() == Qt.Checked:
                has_checked = True
                break
        
        # 如果没有勾选的，看看有没有当前选中的
        if not has_checked:
            has_checked = self.similar_list.currentRow() >= 0
            
        self.click_similar_btn.setEnabled(has_checked)

    def select_all_similar(self):
        """全选相似元素"""
        for i in range(self.similar_list.count()):
            self.similar_list.item(i).setCheckState(Qt.Checked)

    def select_invert_similar(self):
        """反选相似元素"""
        for i in range(self.similar_list.count()):
            item = self.similar_list.item(i)
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)

    def click_selected_similar(self):
        """点击选中的相似元素（支持批量点击勾选的元素）"""
        # 1. 优先获取所有勾选的元素
        checked_indices = []
        for i in range(self.similar_list.count()):
            if self.similar_list.item(i).checkState() == Qt.Checked:
                checked_indices.append(i)
        
        # 2. 如果没有勾选，则获取当前高亮选中的元素
        if not checked_indices:
            current_row = self.similar_list.currentRow()
            if current_row >= 0:
                checked_indices = [current_row]
        
        if not checked_indices:
            return

        self.log_area.append(f"--- 开始批量点击 ({len(checked_indices)}个元素) ---")
        
        async def do_batch_click():
            for idx in checked_indices:
                if idx >= len(self.found_similar_elements):
                    continue
                    
                el = self.found_similar_elements[idx]
                xpath = el['xpath']
                self.log_area.append(f"正在点击 [{idx+1}]: {el['innerText']}")
                
                try:
                    page = self.browser_manager.page
                    try:
                        await page.click(xpath, timeout=3000)
                    except Exception:
                        try:
                            await page.click(xpath, force=True, timeout=2000)
                        except Exception:
                            await page.evaluate(f"""
                                const el = document.evaluate('{xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                if (el) el.click();
                            """)
                    # 批量点击之间增加随机延迟
                    import random
                    await asyncio.sleep(0.5 + random.random())
                except Exception as e:
                    self.log_area.append(f"点击失败 [{idx+1}]: {str(e)}")
            
            self.log_area.append("--- 批量点击完成 ---")
                
        self.browser_manager.run_coroutine(do_batch_click())

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
        self.found_similar_elements = results # 存储结果供点击使用
        self.click_similar_btn.setEnabled(False) # 重置按钮状态
        
        if not results:
            self.log_area.append("未发现相似元素。")
            self.status_bar.showMessage("未发现相似元素")
            return
            
        for el in results:
            text = f"[{el['tagName']}] {el['innerText']} | XPath: {el['xpath']}"
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable) # 使其可勾选
            item.setCheckState(Qt.Unchecked) # 初始未勾选
            self.similar_list.addItem(item)
            
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
