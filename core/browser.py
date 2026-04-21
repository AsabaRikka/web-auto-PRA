import asyncio
import os
from playwright.async_api import async_playwright
import threading

class BrowserManager:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.loop = None
        self._thread = None
        self.storage_state_path = "storage/session.json"

    def start_sync(self):
        """在独立线程中启动浏览器"""
        # 如果事件循环没启动，则启动它
        if not self._thread or not self._thread.is_alive():
            self.loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_event_loop, args=(self.loop,), daemon=True)
            self._thread.start()
        
        # 检查浏览器是否还活着
        future = asyncio.run_coroutine_threadsafe(self._ensure_browser(), self.loop)
        return future.result()

    def _run_event_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def _ensure_browser(self):
        """确保浏览器、上下文和页面都已就绪"""
        if not self.pw:
            self.pw = await async_playwright().start()
            
        if not self.browser or not self.browser.is_connected():
            self.browser = await self.pw.chromium.launch(headless=False)
            self.browser.on("disconnected", self._on_browser_disconnected)
            self.context = None
            self.page = None

        if not self.context:
            storage_state = None
            if os.path.exists(self.storage_state_path):
                storage_state = self.storage_state_path
            self.context = await self.browser.new_context(storage_state=storage_state)
            self.page = None

        if not self.page or self.page.is_closed():
            self.page = await self.context.new_page()
            self.page.on("close", self._on_page_closed)

        return self.page

    def _on_browser_disconnected(self, _):
        """浏览器断开连接时的回调"""
        self.browser = None
        self.context = None
        self.page = None

    def _on_page_closed(self, _):
        """页面关闭时的回调"""
        self.page = None

    async def _launch_browser(self):
        # 这个方法现在被 _ensure_browser 替代，但为了向后兼容暂时保留逻辑
        return await self._ensure_browser()

    async def save_session(self):
        """保存当前登录状态"""
        if self.context:
            os.makedirs("storage", exist_ok=True)
            await self.context.storage_state(path=self.storage_state_path)
            return True
        return False

    async def goto(self, url):
        """打开特定网站"""
        if self.page:
            await self.page.goto(url)
            return True
        return False

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()
        if self.loop:
            self.loop.stop()

    def run_coroutine(self, coro):
        """在浏览器线程中运行协程"""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)
