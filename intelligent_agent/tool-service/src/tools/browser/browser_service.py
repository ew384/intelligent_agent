class BrowserService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context = None
        self.playwright = None
        self.cookies_manager = CookiesManager(config['data_dir'])

