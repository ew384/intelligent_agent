# tool_service/src/tools/script_templates.py
from typing import Dict, Any

class ScriptTemplates:
    """
    提供常用的JavaScript脚本模板
    可以在不同的处理器中重复使用
    """
    
    @staticmethod
    def data_mask_overlay(position="bottom", height_percent=66.7, color="rgba(255, 255, 255, 0.7)", blur=4):
        """
        创建数据遮罩层的脚本模板
        
        Args:
            position: 遮罩位置 ("top", "bottom", "full")
            height_percent: 遮罩高度百分比
            color: 遮罩颜色（RGBA格式）
            blur: 模糊效果强度（像素）
            
        Returns:
            生成的JavaScript脚本
        """
        position_style = {
            "top": f"top: 0; height: {height_percent}%;",
            "bottom": f"bottom: 0; height: {height_percent}%;",
            "full": "top: 0; height: 100%;",
        }.get(position, f"bottom: 0; height: {height_percent}%;")
        
        return """
                <script>
                document.addEventListener('DOMContentLoaded', function() {
                    // 创建遮罩层
                    const overlay = document.createElement('div');
                    
                    // 设置样式
                    overlay.id = 'data-mask-overlay';
                    overlay.style.position = 'fixed';
                    overlay.style.left = '0';
                    overlay.style.width = '100%';
                    overlay.style.height = '66.7%';  // 页面下三分之二
                    overlay.style.bottom = '0';  // 从底部开始
                    overlay.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';  // 半透明白色
                    overlay.style.backdropFilter = 'blur(4px)';  // 添加模糊效果
                    overlay.style.zIndex = '9999';  // 确保在最上层
                    overlay.style.pointerEvents = 'none';  // 允许点击穿透
                    
                    // 添加到页面
                    document.body.appendChild(overlay);
                    
                    console.log("响应拦截器已添加遮罩层");
                }, { once: true });
                </script>
                """
    
    @staticmethod
    def auto_click_button(selector, delay_ms=500):
        """
        创建自动点击按钮的脚本模板
        
        Args:
            selector: 要点击的元素选择器
            delay_ms: 延迟时间（毫秒）
            
        Returns:
            生成的JavaScript脚本
        """
        return f"""
        setTimeout(function() {{
            const button = document.querySelector('{selector}');
            if (button) {{
                button.click();
                console.log('Auto-clicked element: {selector}');
            }} else {{
                console.warn('Element not found: {selector}');
            }}
        }}, {delay_ms});
        """
    
    @staticmethod
    def form_auto_fill(field_values):
        """
        创建自动填充表单的脚本模板
        
        Args:
            field_values: 字段名和值的字典 {"field_id": "value"}
            
        Returns:
            生成的JavaScript脚本
        """
        fill_statements = []
        for field_id, value in field_values.items():
            fill_statements.append(f"""
            const {field_id}_field = document.getElementById('{field_id}');
            if ({field_id}_field) {{
                {field_id}_field.value = '{value}';
                // 触发change事件以便表单验证
                const event = new Event('change', {{ bubbles: true }});
                {field_id}_field.dispatchEvent(event);
                console.log('Filled field: {field_id}');
            }}
            """)
        
        return """
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
        """ + "\n".join(fill_statements) + """
            }, 500);
        }, { once: true });
        """
    
    @staticmethod
    def disable_page_elements(selectors):
        """
        创建禁用页面元素的脚本模板
        
        Args:
            selectors: 要禁用的元素选择器列表
            
        Returns:
            生成的JavaScript脚本
        """
        disable_statements = []
        for selector in selectors:
            disable_statements.append(f"""
            document.querySelectorAll('{selector}').forEach(function(element) {{
                element.disabled = true;
                element.style.opacity = '0.5';
                element.style.pointerEvents = 'none';
            }});
            """)
        
        return """
        document.addEventListener('DOMContentLoaded', function() {
        """ + "\n".join(disable_statements) + """
        }, { once: true });
        """