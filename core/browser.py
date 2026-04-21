import asyncio
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

    def start_sync(self):
        """在独立线程中启动浏览器"""
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_event_loop, args=(self.loop,), daemon=True)
        self._thread.start()
        
        future = asyncio.run_coroutine_threadsafe(self._launch_browser(), self.loop)
        return future.result()

    def _run_event_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def _launch_browser(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=False)
        # 持久化上下文（保存登录状态）
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self.page

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
