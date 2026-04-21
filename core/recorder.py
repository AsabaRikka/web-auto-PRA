import asyncio
import json

class Recorder:
    def __init__(self, browser_manager, on_step_recorded):
        self.browser_manager = browser_manager
        self.on_step_recorded = on_step_recorded # 回调函数，通知 UI
        self.is_recording = False

    async def start(self):
        self.is_recording = True
        
        # 记录脚本内容
        recorder_script = """
        (function() {
            if (window.__web_auto_recorder_injected) return;
            window.__web_auto_recorder_injected = true;

            function getXPath(element) {
                try {
                    if (element.id && !/\\d{4,}/.test(element.id) && element.id.length < 50) {
                        return 'id("' + element.id + '")';
                    }
                    if (element === document.body) return 'body';
                    
                    let ix = 0;
                    let siblings = element.parentNode ? element.parentNode.childNodes : [];
                    for (let i = 0; i < siblings.length; i++) {
                        let sibling = siblings[i];
                        if (sibling === element) {
                            const parentPath = element.parentNode ? getXPath(element.parentNode) : '';
                            const path = (parentPath ? parentPath + '/' : '') + element.tagName.toLowerCase();
                            return ix === 0 ? path : path + '[' + (ix + 1) + ']';
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            ix++;
                        }
                    }
                } catch (e) { return 'unknown'; }
                return '';
            }

            window.addEventListener('mousedown', (e) => {
                let element = e.target;
                
                const isSvgRelated = (el) => {
                    const tag = el.tagName.toLowerCase();
                    return tag === 'svg' || tag === 'path' || tag === 'use' || tag === 'circle' || tag === 'rect';
                };

                if (isSvgRelated(element)) {
                    let parent = element.parentElement;
                    while (parent && parent !== document.body) {
                        const parentTag = parent.tagName.toLowerCase();
                        const style = window.getComputedStyle(parent);
                        if (parentTag === 'button' || parentTag === 'a' || style.cursor === 'pointer' || parent.getAttribute('role') === 'button') {
                            element = parent;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                }

                let clickable = element;
                while (clickable && clickable !== document.body) {
                    const style = window.getComputedStyle(clickable);
                    if (clickable.tagName === 'BUTTON' || clickable.tagName === 'A' || style.cursor === 'pointer' || clickable.getAttribute('role') === 'button') {
                        element = clickable;
                        break;
                    }
                    clickable = clickable.parentElement;
                }
                
                if (!element) element = e.target;

                const step = {
                    type: 'click',
                    tagName: element.tagName,
                    innerText: (element.innerText || "").substring(0, 30).replace(/\\n/g, ' ').trim(),
                    xpath: getXPath(element)
                };
                
                if (window.onStep) window.onStep(step);
            }, true);

            window.addEventListener('input', (e) => {
                const element = e.target;
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    const step = {
                        type: 'input',
                        tagName: element.tagName,
                        value: element.value,
                        xpath: getXPath(element)
                    };
                    if (window.onStep) window.onStep(step);
                }
            }, true);
        })();
        """

        async def inject_to_page(page):
            """将脚本注入到指定页面"""
            try:
                # 暴露回调
                try:
                    await page.expose_binding("onStep", lambda source, data: self._on_step_callback(source, data, page))
                except Exception:
                    pass
                
                # 注入初始加载
                await page.add_init_script(recorder_script)
                
                # 立即在所有 frame 中执行
                for frame in page.frames:
                    try:
                        await frame.evaluate(recorder_script)
                    except:
                        pass
            except Exception as e:
                print(f"注入页面失败: {e}")

        # 设置 BrowserManager 的新页面回调
        self.browser_manager.on_page_created_callback = inject_to_page
        
        # 立即对当前所有已打开的页面进行注入
        for page in self.browser_manager.pages:
            await inject_to_page(page)

    def _on_step_callback(self, source, step_data, page):
        if self.is_recording:
            # 记录该步骤发生的页面索引
            try:
                page_index = self.browser_manager.pages.index(page)
            except ValueError:
                page_index = 0
                
            step_data['page_index'] = page_index
            description = self._generate_description(step_data)
            step_data['description'] = f"[标签页{page_index+1}] {description}"
            self.on_step_recorded(step_data)

    def _generate_description(self, step):
        t = step['type']
        if t == 'click':
            return f"点击了 {step['tagName']} 元素: {step['innerText']}"
        elif t == 'input':
            return f"在输入框中输入了: {step['value']}"
        return "未知操作"

    def stop(self):
        self.is_recording = False
