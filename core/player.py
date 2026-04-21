import asyncio

class Player:
    def __init__(self, browser_manager, on_step_status_change):
        self.browser_manager = browser_manager
        self.on_step_status_change = on_step_status_change # 回调，更新 UI 上的状态
        self.is_playing = False

    async def play(self, steps):
        self.is_playing = True

        for i, step in enumerate(steps):
            if not self.is_playing:
                break
            
            # 通知 UI 步骤开始执行
            self.on_step_status_change(i, "executing")
            
            try:
                # 确定要在哪个页面上执行操作
                page_index = step.get('page_index', 0)
                if page_index < len(self.browser_manager.pages):
                    page = self.browser_manager.pages[page_index]
                    # 将该页面带到前台
                    await page.bring_to_front()
                else:
                    # 如果找不到对应的标签页，回退到当前活跃页面
                    page = self.browser_manager.page
                
                # 模拟人类停留时间
                wait_time = step.get('wait_time', 1000) / 1000.0
                await asyncio.sleep(wait_time)

                if step['type'] == 'click':
                    # 增强型点击
                    try:
                        await page.click(step['xpath'], timeout=5000)
                    except Exception:
                        try:
                            await page.click(step['xpath'], force=True, timeout=3000)
                        except Exception:
                            await page.evaluate(f"""
                                const el = document.evaluate('{step['xpath']}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                if (el) el.click();
                            """)
                elif step['type'] == 'input':
                    await page.fill(step['xpath'], step['value'], timeout=5000)
                
                # 通知 UI 步骤执行成功
                self.on_step_status_change(i, "success")
            except Exception as e:
                # 通知 UI 步骤执行失败，并提示错误
                self.on_step_status_change(i, f"failed: {str(e)}")
                break
        
        self.is_playing = False

    def stop(self):
        self.is_playing = False
