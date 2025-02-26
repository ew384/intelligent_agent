# tool-service/src/tools/browser/browser_service.py
from typing import Dict, Any, Optional
import logging
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from ..common.cookies_manager import CookiesManager

logger = logging.getLogger(__name__)
        
class BrowserService:
    def __init__(self, headless: bool = False, config: Dict[str, Any] = None):
        """
        Initialize the browser service
        
        Args:
            headless: Whether to run the browser in headless mode
            config: Additional configuration options
        """
        self.headless = headless
        self.config = config or {
            'data_dir': os.environ.get('BROWSER_DATA_DIR', './browser_data'),
            'timeout': int(os.environ.get('BROWSER_TIMEOUT', 30000)),
            'user_agent': os.environ.get(
                'BROWSER_USER_AGENT', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
            )
        }
        self.playwright = None
        self.browser = None
        self.context = None
        
        # 创建基础数据目录 - 修复这里的错误，确保先创建data_dir
        self.data_dir = Path(self.config['data_dir'])
        self.screenshots_dir = self.data_dir / 'screenshots'
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # 添加用户数据目录
        self.user_data_dir = self.data_dir / 'user_data'
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_manager = CookiesManager(self.data_dir)
        
        
    async def initialize(self) -> Page:
        """Initialize browser and create a new page"""
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
                
            if not hasattr(self, 'user_data_dir'):
                self.user_data_dir = Path(self.config['data_dir']) / 'user_data'
                self.user_data_dir.mkdir(parents=True, exist_ok=True)
            if not self.browser:
                browser_args = [
                        '--disable-blink-features=AutomationControlled',
                        '--disable-automation',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        '--window-size=1920,1080',
                        '--disable-gpu',
                        '--lang=zh-CN,zh,en-US,en',  # 语言设置
                        '--accept-lang=zh-CN,zh,en-US,en',
                ]
               # if hasattr(self, 'user_data_dir') and self.user_data_dir.exists():
               #     browser_args.append(f'--user-data-dir={self.user_data_dir}')
                # 使用更多的参数来模拟真实浏览器
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=browser_args
                )
                
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless
            )
            # 创建具有更真实配置的上下文
            #self.context = await self.browser.new_context(
            #    viewport={'width': 1920, 'height': 1080},
            #    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            #    locale='zh-CN',
            #    timezone_id='Asia/Shanghai',
            #    color_scheme='light',
            #    device_scale_factor=1,
            #    is_mobile=False,
            #    has_touch=False,
            #    java_script_enabled=True,
            #    ignore_https_errors=True,
            #    bypass_csp=True,  # 绕过内容安全策略
            #    permissions=['geolocation', 'notifications']  # 允许一些权限
            #)
            

            # 修改 WebDriver 相关属性，减少自动化特征
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            # 更强大的反检测脚本
            await self.context.add_init_script("""
            // 重新定义navigator和webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // 隐藏自动化特征
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // 修改userAgent信息
            const originalGetUserAgent = navigator.userAgent;
            Object.defineProperty(navigator, 'userAgent', {
                get: () => originalGetUserAgent.replace('Headless', '')
            });
            
            // 添加更多正常浏览器的特征
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        name: "Chrome PDF Viewer" 
                    },
                    {
                        0: {type: "application/x-google-chrome-pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        name: "Native Client"
                    }
                ]
            });
            
            // 伪造语言设置
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en']
            });
            
            // 伪造硬件并发性
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // 伪造设备内存
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // 模拟屏幕信息
            Object.defineProperty(screen, 'width', {get: () => 1920});
            Object.defineProperty(screen, 'height', {get: () => 1080});
            Object.defineProperty(screen, 'availWidth', {get: () => 1920});
            Object.defineProperty(screen, 'availHeight', {get: () => 1040});
            Object.defineProperty(screen, 'colorDepth', {get: () => 24});
            Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
            
            // 添加常见的媒体设备
            const getMediaFn = MediaDevices.prototype.getDisplayMedia;
            MediaDevices.prototype.getDisplayMedia = function() {
                return new Promise((resolve, reject) => {
                    getMediaFn.call(this, arguments)
                        .then(stream => resolve(stream))
                        .catch(e => reject(e));
                });
            };
            """)
            
            # 创建页面
            page = await self.context.new_page()
            await page.set_default_timeout(self.config['timeout'])
            
            # 模拟更真实的人类行为
            await self._setup_human_behavior(page)
            
            logger.info("浏览器服务初始化成功，已应用反检测措施")
            return page
        except Exception as e:
            logger.error(f"浏览器初始化失败: {str(e)}")
            await self.cleanup()
            return None
            
    async def navigate_humanlike(self, page: Page, url: str) -> bool:
        """像人类一样导航到URL"""
        try:
            # 随机延迟
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 访问URL
            await page.goto(url, wait_until='domcontentloaded')
            
            # 随机滚动行为
            await self._random_scroll(page)
            
            # 等待页面完全加载
            await page.wait_for_load_state('networkidle')
            
            logger.info(f"已像人类一样导航到: {url}")
            return True
        except Exception as e:
            logger.error(f"导航失败: {str(e)}")
            return False
    
    async def _random_scroll(self, page: Page):
        """随机滚动行为"""
        try:
            # 获取页面高度
            height = await page.evaluate('() => document.body.scrollHeight')
            
            # 随机选择1-3次滚动
            scroll_times = random.randint(1, 3)
            
            for _ in range(scroll_times):
                # 随机选择滚动位置
                scroll_y = random.randint(100, max(height, 200))
                
                # 平滑滚动
                await page.evaluate(f'window.scrollTo({{top: {scroll_y}, behavior: "smooth"}})')
                
                # 随机等待
                await asyncio.sleep(random.uniform(0.5, 2.0))
        except Exception as e:
            logger.warning(f"随机滚动时出错: {str(e)}")
    
    async def click_humanlike(self, page: Page, selector: str) -> bool:
        """像人类一样点击元素"""
        try:
            # 查找元素
            element = await page.wait_for_selector(selector, timeout=5000)
            if not element:
                logger.warning(f"未找到元素: {selector}")
                return False
            
            # 获取元素的位置和大小
            box = await element.bounding_box()
            if not box:
                logger.warning(f"无法获取元素尺寸: {selector}")
                return False
            
            # 计算点击位置（随机位置但在元素范围内）
            x = box["x"] + random.uniform(5, box["width"] - 5)
            y = box["y"] + random.uniform(5, box["height"] - 5)
            
            # 先将鼠标移动到元素附近，再移动到具体位置
            await page.mouse.move(x - random.uniform(10, 20), y - random.uniform(10, 20))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.2))
            
            # 点击
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.05, 0.1))
            await page.mouse.up()
            
            # 等待一下
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            return True
        except Exception as e:
            logger.error(f"点击元素失败: {str(e)}")
            return False
    
    async def type_humanlike(self, page: Page, selector: str, text: str) -> bool:
        """像人类一样输入文本"""
        try:
            # 查找元素
            element = await page.wait_for_selector(selector, timeout=5000)
            if not element:
                return False
            
            # 点击元素
            await self.click_humanlike(page, selector)
            
            # 清除现有文本
            await page.fill(selector, "")
            
            # 逐个字符输入，模拟人类输入速度
            for char in text:
                await page.type(selector, char, delay=random.uniform(50, 150))
                
            # 随机等待
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            return True
        except Exception as e:
            logger.error(f"输入文本失败: {str(e)}")
            return False
    
    async def _setup_human_behavior(self, page: Page):
        """设置更像人类的浏览行为"""
        # 设置用户代理标头
        await page.set_extra_http_headers({
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'sec-ch-ua': '"Google Chrome";v="122", "Not(A:Brand";v="24", "Chromium";v="122"',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-mobile': '?0'
        })
        
        # 定义随机移动函数
        await page.evaluate('''
        () => {
            // 添加随机移动
            const randomMovement = () => {
                if (Math.random() > 0.7) {
                    const x = Math.floor(Math.random() * window.innerWidth);
                    const y = Math.floor(Math.random() * window.innerHeight);
                    const event = new MouseEvent('mousemove', {
                        clientX: x,
                        clientY: y,
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                }
                
                setTimeout(randomMovement, Math.random() * 5000 + 1000);
            };
            
            randomMovement();
        }
        ''')

    async def _setup_extensions(self, context):
        """设置常见的浏览器扩展"""
        try:
            # 这需要你预先准备扩展文件，例如从Chrome Web Store下载
            extensions_dir = self.data_dir / 'extensions'
            if not extensions_dir.exists():
                return
    
            # 加载已有扩展
            for ext_dir in extensions_dir.iterdir():
                if ext_dir.is_dir():
                    try:
                        await context.add_cdp_extension(str(ext_dir))
                        logger.info(f"已加载扩展: {ext_dir.name}")
                    except Exception as e:
                        logger.warning(f"加载扩展 {ext_dir.name} 失败: {str(e)}")
        except Exception as e:
            logger.error(f"设置扩展时出错: {str(e)}")
    async def new_page(self) -> Page:
        """
        Create a new page in the existing browser context
        
        Returns:
            A new page object
        """
        if not self.context:
            # Initialize browser if not already done
            await self.initialize()
            
        return await self.context.new_page()

    async def _ensure_page_ready(self, page: Page):
        """确保页面完全加载并且布局稳定"""
        try:
            # 等待网络请求完成
            await page.wait_for_load_state('networkidle', timeout=30000)

            # 等待 DOM 内容加载完成
            await page.wait_for_load_state('domcontentloaded', timeout=30000)

            # 等待页面可见元素加载
            try:
                # 等待页面主要内容区域
                await page.wait_for_selector('body', state='visible', timeout=5000)
            except Exception as e:
                logger.warning(f"Selector wait warning: {str(e)}")

            # 等待一小段时间确保渲染完成
            await page.wait_for_timeout(2000)

        except Exception as e:
            logger.warning(f"Page stabilization warning: {str(e)}")

    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            logger.info("浏览器资源清理被临时禁用，用于调试目的")
            # 临时注释掉关闭代码，以便查看浏览器状态
            # if self.context:
            #     await self.context.close()
            #     self.context = None
            #     
            # if self.browser:
            #     await self.browser.close()
            #     self.browser = None
            #     
            # if self.playwright:
            #     await self.playwright.stop()
            #     self.playwright = None
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
