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
        
        # 增强版录制脚本
        recorder_script = """
        (function() {
            if (window.__web_auto_recorder_injected) return;
            window.__web_auto_recorder_injected = true;

            console.log('[Recorder] 注入成功，开始监听点击事件...');

            function getXPath(element) {
                try {
                    if (element.id && !/\\d{4,}/.test(element.id) && element.id.length < 50) {
                        return '//*[@id="' + element.id + '"]';
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

            // 使用 mousedown 捕获，因为它比 click 更难被阻止
            window.addEventListener('mousedown', (e) => {
                let element = e.target;
                
                // --- 核心优化：SVG/Path 归一化逻辑 ---
                // 如果点到了 svg 或 path，强制寻找它的父级按钮或链接
                const isSvgRelated = (el) => {
                    const tag = el.tagName.toLowerCase();
                    return tag === 'svg' || tag === 'path' || tag === 'use' || tag === 'circle' || tag === 'rect';
                };

                if (isSvgRelated(element)) {
                    let parent = element.parentElement;
                    while (parent && parent !== document.body) {
                        const parentTag = parent.tagName.toLowerCase();
                        const style = window.getComputedStyle(parent);
                        // 如果父级是按钮、链接，或者有指针手势，就认为它是真正的点击目标
                        if (parentTag === 'button' || 
                            parentTag === 'a' || 
                            style.cursor === 'pointer' || 
                            parent.getAttribute('role') === 'button') {
                            element = parent;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                }

                // 继续向上寻找最近的可点击祖先（针对普通元素）
                let clickable = element;
                while (clickable && clickable !== document.body) {
                    const style = window.getComputedStyle(clickable);
                    if (clickable.tagName === 'BUTTON' || 
                        clickable.tagName === 'A' || 
                        style.cursor === 'pointer' ||
                        clickable.getAttribute('role') === 'button') {
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
                
                console.log('[Recorder] 记录步骤:', step.description || step.innerText);
                if (window.onStep) {
                    window.onStep(step);
                } else {
                    console.error('[Recorder] window.onStep 未定义！');
                }
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

        try:
            # 暴露回调接口，handle=True 允许在所有 frame 中访问
            await page.expose_binding("onStep", self._on_step_callback)
        except Exception:
            pass
            
        # 监听控制台消息，方便我们在 Python 端看到浏览器的报错
        page.on("console", lambda msg: print(f"浏览器控制台: {msg.text}"))
        
        # 注入初始加载
        await page.add_init_script(recorder_script)
        
        # 立即注入到当前所有 Frame
        for frame in page.frames:
            try:
                await frame.evaluate(recorder_script)
            except Exception as e:
                print(f"注入 Frame 失败: {e}")

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
