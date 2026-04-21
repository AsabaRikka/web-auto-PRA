import asyncio

class Player:
    def __init__(self, browser_manager, on_step_status_change):
        self.browser_manager = browser_manager
        self.on_step_status_change = on_step_status_change # 回调，更新 UI 上的状态
        self.is_playing = False

    async def play(self, steps):
        """普通顺序执行"""
        self.is_playing = True
        page = self.browser_manager.page

        for i, step in enumerate(steps):
            if not self.is_playing: break
            self.on_step_status_change(i, "executing")
            try:
                selector = f"xpath={step['xpath']}"
                if step['type'] == 'click':
                    await page.click(selector, timeout=5000)
                elif step['type'] == 'input':
                    await page.fill(selector, step['value'], timeout=5000)
                self.on_step_status_change(i, "success")
            except Exception as e:
                self.on_step_status_change(i, f"failed: {str(e)}")
                break
        self.is_playing = False

    async def play_batch(self, step, max_count=None):
        """批量执行某个步骤（针对页面上所有匹配的元素）"""
        self.is_playing = True
        page = self.browser_manager.page
        
        # 1. 自动泛化 XPath（去掉最后的索引 [n]，匹配同类所有元素）
        xpath = step['xpath']
        general_xpath = xpath
        if '[' in xpath:
            last_bracket = xpath.rfind('[')
            general_xpath = xpath[:last_bracket]
            
        print(f"[Player] 开始批量操作，泛化 XPath: {general_xpath}")
        
        try:
            # 2. 找到页面上所有符合条件的元素
            elements = await page.query_selector_all(f"xpath={general_xpath}")
            total = len(elements)
            if max_count:
                total = min(total, max_count)
            print(f"[Player] 发现并限制执行数量为: {total}")
            
            for i in range(total):
                if not self.is_playing: break
                
                # 重新获取元素（防止页面刷新导致引用失效）
                current_elements = await page.query_selector_all(f"xpath={general_xpath}")
                if i >= len(current_elements): break
                
                target = current_elements[i]
                # 滚动到视口（模拟人类）
                await target.scroll_into_view_if_needed()
                # 随机延迟（模拟人类）
                import random
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # 执行点击
                await target.click(force=True)
                self.on_step_status_change(0, f"批量执行中: {i+1}/{total}")
                
            self.on_step_status_change(0, f"批量完成，共处理 {total} 个元素")
        except Exception as e:
            self.on_step_status_change(0, f"批量操作失败: {str(e)}")
            
        self.is_playing = False

    def stop(self):
        self.is_playing = False
