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
        self.pages = [] # 存储所有打开的页面
        self.loop = None
        self._thread = None
        self.storage_state_path = "storage/session.json"
        self.on_page_created_callback = None # 新页面创建时的回调

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
            # 这里的启动参数非常关键，用于模拟原生浏览器
            self.browser = await self.pw.chromium.launch(
                headless=False,
                args=[
                    "--start-maximized", 
                    "--disable-blink-features=AutomationControlled" # 隐藏自动化标记
                ],
                ignore_default_args=["--enable-automation"] # 进一步隐藏自动化
            )
            self.browser.on("disconnected", self._on_browser_disconnected)
            self.context = None
            self.page = None
            self.pages = []

        if not self.context:
            storage_state = None
            if os.path.exists(self.storage_state_path):
                storage_state = self.storage_state_path
            
            # 核心修复：
            # 1. no_viewport=True 告诉 Playwright 放弃对分辨率的控制，改由窗口大小控制
            # 2. 设置 User-Agent 使其更像真实浏览器，触发百度等网站的自适应逻辑
            self.context = await self.browser.new_context(
                storage_state=storage_state,
                no_viewport=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.context.on("page", self._on_playwright_page_created)
            self.page = None

        if not self.page or self.page.is_closed():
            self.page = await self.context.new_page()
            # self.page 已经在 _on_playwright_page_created 中处理了

        return self.page

    async def _on_playwright_page_created(self, page):
        """Playwright 监听到新页面打开"""
        if page not in self.pages:
            self.pages.append(page)
            if not self.page or self.page.is_closed():
                self.page = page
            
            # 监听页面关闭
            page.on("close", lambda p: self._on_page_closed(p))
            
            # 如果有外部回调（如 Recorder 需要注入脚本），则执行
            if self.on_page_created_callback:
                await self.on_page_created_callback(page)

    def _on_browser_disconnected(self, _):
        """浏览器断开连接时的回调"""
        self.browser = None
        self.context = None
        self.page = None
        self.pages = []

    def _on_page_closed(self, page):
        """页面关闭时的回调"""
        if page in self.pages:
            self.pages.remove(page)
        if self.page == page:
            self.page = self.pages[-1] if self.pages else None

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

    async def find_similar_elements(self, xpath):
        """搜索与给定 XPath 相似的元素"""
        if not self.page:
            return []
            
        script = f"""
        (function() {{
            const target = document.evaluate('{xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (!target) return [];
            
            const tagName = target.tagName;
            const className = target.className;
            
            // 简单策略：寻找相同标签且类名相似的元素
            let similarElements = [];
            const allElements = document.getElementsByTagName(tagName);
            
            for (let el of allElements) {{
                if (el === target) continue;
                
                // 相似度判断：类名完全一致或者包含主要类名
                if (el.className === className && className !== "") {{
                    similarElements.push({{
                        tagName: el.tagName,
                        className: el.className,
                        innerText: (el.innerText || "").substring(0, 30).trim(),
                        xpath: getXPath(el) // 这里复用 recorder 里的 getXPath 逻辑
                    }});
                }}
            }}

            function getXPath(element) {{
                if (element.id && !/\\d{{4,}}/.test(element.id) && element.id.length < 50) {{
                    return 'id("' + element.id + '")';
                }}
                if (element === document.body) return 'body';
                let ix = 0;
                let siblings = element.parentNode ? element.parentNode.childNodes : [];
                for (let i = 0; i < siblings.length; i++) {{
                    let sibling = siblings[i];
                    if (sibling === element) {{
                        const parentPath = element.parentNode ? getXPath(element.parentNode) : '';
                        const path = (parentPath ? parentPath + '/' : '') + element.tagName.toLowerCase();
                        return ix === 0 ? path : path + '[' + (ix + 1) + ']';
                    }}
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                }}
                return '';
            }}
            
            return similarElements;
        }})();
        """
        try:
            results = await self.page.evaluate(script)
            return results
        except Exception as e:
            print(f"搜索相似元素失败: {e}")
            return []

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
