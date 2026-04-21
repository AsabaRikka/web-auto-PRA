import asyncio
import json

class Recorder:
    def __init__(self, browser_manager, on_step_recorded):
        self.browser_manager = browser_manager
        self.on_step_recorded = on_step_recorded # 回调函数，通知 UI
        self.is_recording = False

    async def start(self):
        self.is_recording = True
        page = self.browser_manager.page
        
        # 注入录制脚本
        await page.expose_binding("onStep", self._on_step_callback)
        await page.add_init_script("""
            window.addEventListener('click', (e) => {
                const element = e.target;
                const step = {
                    type: 'click',
                    tagName: element.tagName,
                    id: element.id,
                    className: element.className,
                    innerText: element.innerText.substring(0, 20),
                    xpath: getXPath(element)
                };
                window.onStep(step);
            }, true);

            window.addEventListener('input', (e) => {
                const element = e.target;
                const step = {
                    type: 'input',
                    tagName: element.tagName,
                    value: element.value,
                    xpath: getXPath(element)
                };
                window.onStep(step);
            }, true);

            function getXPath(element) {
                if (element.id !== '') return 'id("' + element.id + '")';
                if (element === document.body) return element.tagName;
                var ix = 0;
                var siblings = element.parentNode.childNodes;
                for (var i = 0; i < siblings.length; i++) {
                    var sibling = siblings[i];
                    if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                }
            }
        """)
        
        # 针对当前已经加载的页面也注入一次（如果是开始录制时页面已打开）
        await page.evaluate("""
            // 重复上面的事件监听逻辑
        """)

    def _on_step_callback(self, source, step_data):
        if self.is_recording:
            # 格式化自然语言描述
            description = self._generate_description(step_data)
            step_data['description'] = description
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
