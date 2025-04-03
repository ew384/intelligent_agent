import streamlit as st
import asyncio
import sys

# 最重要的是：st.set_page_config 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="中信银行信用卡中心",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入应用类
from credit_card_agent import CreditCardAgentApp

# 使用命令行参数控制是否使用模拟工具
use_mock = False#"--mock" in sys.argv

class ModifiedCreditCardAgentApp(CreditCardAgentApp):
    def __init__(self, use_mock_tools=False):
        # 不要在这里调用 st.set_page_config，而是在外部调用
        
        # 应用自定义 CSS
        self.apply_custom_css()
        
        # 初始化会话状态
        self.init_session_state()
        
        # 初始化工具
        self.tools = self.setup_mock_tools() if use_mock_tools else self.setup_tools()
        
        # 设置代理
        self.agent = self.create_agent(use_mock_api=use_mock_tools)
        
        # 用于存储最后一次用户查询的变量
        self._last_user_query = ""

def main():
    st.title("中信银行信用卡分期经理 " + ("(测试模式)" if use_mock else ""))
    
    # 创建应用实例，使用模拟工具和 API
    app = ModifiedCreditCardAgentApp(use_mock_tools=use_mock)
    
    # 如果在测试模式下，添加一个提示
    if use_mock:
        st.info("当前运行在测试模式下，使用模拟工具和 API。")
    
    # 运行应用
    app.run()

if __name__ == "__main__":
    main()
