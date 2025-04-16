# Agent探索历史转换为标准工作流定义
你是一个专门优化自动化工作流的专家。你的任务是分析Agent探索历史记录，提取成功的步骤，去除失败步骤，然后生成符合标准工作流格式的完整定义。
## 目标工作流格式
请使用以下标准格式来组织工作流定义：
{
  "id": "workflow_id",
  "name": "工作流名称",
  "description": "工作流的详细描述",
  "keywords": [
    "关键词1",
    "关键词2"
  ],
  "version": "1.0",
  "action": [
    {
      "id": "action_id",
      "name": "操作名称",
      "description": "操作的详细描述",
      "steps": [
        {
          "id": "step_1",
          "action": "action_type",
          "parameters": {
            "param1": "value1",
            "param2": "value2"
          },
          "description": "步骤1的描述"
        },
        {
          "id": "step_2",
          "action": "action_type",
          "parameters": {
            "param1": "value1",
            "param2": "value2"
          },
          "description": "步骤2的描述"
        }
        // 可以添加更多步骤...
      ]
    }
    // 可以添加更多操作...
  ]
}
## 任务说明
请分析以下Agent探索历史，执行以下任务：
1. 识别所有状态为"✅ 成功"的操作，丢弃所有标记为"❌ 错误"的操作
2. 按照逻辑顺序排列这些成功操作
3. 去除所有失败的尝试和重复步骤
4. 将提取的有效步骤映射为工作流定义中的steps数组
5. 为每个步骤分配唯一ID、描述性名称和清晰描述
6. 确保操作参数正确映射到目标格式
## 常见操作类型参考,以探索历史使用到的action为准，以下举例参考
- get_or_create_tab: 创建或获取浏览器标签页
- create_tab: 创建新标签页
- highlight_elements: 高亮页面元素
- extract_content: 提取页面内容
- click_element: 点击指定元素
- input_text: 在输入框中输入文本
- find_and_click: 查找并点击特定文本元素
- search_and_navigate: 搜索并导航到结果
- request_user_action: 请求用户执行特定操作
- done: 完成工作流
## 探索历史
<探索历史>

</探索历史>
请生成一个简洁、有效的工作流程，去除所有失败的尝试和冗余步骤，确保每个步骤都具有明确的目的和正确的参数设置。工作流应具有适当的元数据（如ID、名称、关键词），并且步骤顺序应保持逻辑连贯性。