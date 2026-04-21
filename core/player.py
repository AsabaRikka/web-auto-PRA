import asyncio

class Player:
    def __init__(self, browser_manager, on_step_status_change):
        self.browser_manager = browser_manager
        self.on_step_status_change = on_step_status_change # 回调，更新 UI 上的状态
        self.is_playing = False

    async def play(self, steps):
        self.is_playing = True
        page = self.browser_manager.page

        for i, step in enumerate(steps):
            if not self.is_playing:
                break
            
            # 通知 UI 步骤开始执行
            self.on_step_status_change(i, "executing")
            
            try:
                # 模拟人类停留时间
                wait_time = step.get('wait_time', 1000) / 1000.0
                await asyncio.sleep(wait_time)

                if step['type'] == 'click':
                    await page.click(step['xpath'])
                elif step['type'] == 'input':
                    await page.fill(step['xpath'], step['value'])
                
                # 通知 UI 步骤执行成功
                self.on_step_status_change(i, "success")
            except Exception as e:
                # 通知 UI 步骤执行失败，并提示错误
                self.on_step_status_change(i, f"failed: {str(e)}")
                break
        
        self.is_playing = False

    def stop(self):
        self.is_playing = False
