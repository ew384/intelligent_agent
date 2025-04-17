# Agent探索历史转换为标准工作流定义

你是一个专门优化自动化工作流的专家。你的任务是分析Agent探索历史记录，提取成功的步骤，去除失败步骤，然后生成符合标准工作流格式的完整定义。

## 目标工作流格式

请使用以下标准格式来组织工作流定义：

```json
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
```

## 任务说明

请分析以下Agent探索历史，执行以下任务：

1. 识别所有状态为"✅ 成功"的操作，丢弃所有标记为"❌ 错误"的操作
2. 按照逻辑顺序排列这些成功操作
3. 去除所有失败的尝试和重复步骤
4. 将提取的有效步骤映射为工作流定义中的steps数组
5. 为每个步骤分配唯一ID、描述性名称和清晰描述
6. 确保操作参数正确映射到目标格式

## 特殊处理说明

### 用户登录操作优化

当发现探索历史中包含以下连续步骤模式时：
1. `request_user_action`类型为"login"的操作，请求用户手动登录
2. 紧随其后的`evaluate_state`操作，用于确认用户已登录状态

请将这两个步骤合并，并转换为`check_condition_and_execute`操作，格式如下：

```json
{
  "id": "step_x",
  "action": "check_condition_and_execute",
  "parameters": {
    "condition_check": {
      "type": "is_logged_in",
      "parameters": {
        "login_button_text": "登录",
        "user_element_text": "用户名" // 根据具体情况调整
      }
    },
    "action_if_true": {
      "wait": {
        "time": 0.5,
        "message": "用户已登录，跳过登录步骤"
      }
    },
    "action_if_false": {
      "request_user_action": {
        "type": "login",
        "message": "请登录您的账号", // 使用原有request_user_action中的message
        "description": "需要您手动完成账号的登录，以便继续执行下一步操作。" // 使用原有request_user_action中的description
      }
    }
  },
  "description": "检查用户登录状态并处理" // 组合两个步骤的描述
}
```

### 其他用户交互操作优化

对于其他类型的用户交互操作（如验证码输入、选择等），也应尽可能检测前置条件，转换为`check_condition_and_execute`模式，避免每次执行工作流都需要用户干预。

## 常见操作类型参考，以探索历史的action为准，以下举例参考

- get_or_create_tab: 创建或获取浏览器标签页
- create_tab: 创建新标签页
- extract_content: 提取页面内容
- click_element: 点击指定元素
- input_text: 在输入框中输入文本
- find_and_click: 查找并点击特定文本元素
- search_and_navigate: 搜索并导航到结果
- request_user_action: 请求用户执行特定操作
- evaluate_state: 评估当前页面状态
- check_condition_and_execute: 检查条件并执行相应操作
- done: 完成工作流

## 探索历史

<探索历史>