# intelligent-agent
## 项目结构

```
intelligent-agent/
├── README.md                     # 项目文档
├── Makefile                     # 构建和运行脚本
├── docker-compose.yml           # Docker编排配置
├── requirements.txt             # 公共依赖
│
├── api-gateway/                 # API网关服务
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py             # FastAPI应用入口
│       ├── config/             # 配置文件
│       │   └── settings.py
│       ├── core/               # 核心功能
│       │   ├── auth.py         # 认证和授权
│       │   ├── security.py     # 安全相关
│       │   └── middleware.py   # 中间件
│       ├── routes/             # API路由
│       │   ├── tasks.py        # 任务管理
│       │   └── tools.py        # 工具调用
│       └── clients/            # 服务客户端
│           └── orchestrator.py  # 编排服务客户端
│
├── orchestrator-service/        # 任务编排服务
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py             # 服务入口
│       ├── config/
│       │   └── settings.py
│       ├── core/
│       │   ├── orchestrator.py  # 编排核心
│       │   └── agent.py        # Agent实现
│       ├── workflows/          # 工作流定义
│       │   ├── base.py        # 基础工作流
│       │   ├── ecommerce.py   # 电商场景
│       │   └── hr.py          # HR场景
│       └── clients/           # 服务客户端
│           ├── scenario.py    # 场景服务
│           └── tool.py        # 工具服务
│
├── scenario-service/           # 场景服务
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py            # 服务入口
│       ├── config/
│       │   └── settings.py
│       ├── models/            # 数据模型
│       │   ├── scenario.py    # 场景模型
│       │   └── workflow.py    # 工作流模型
│       ├── scenarios/         # 场景定义
│       │   ├── ecommerce/     # 电商场景
│       │   │   ├── search.py  # 商品搜索
│       │   │   └── compare.py # 价格对比
│       │   └── hr/            # HR场景
│       │       ├── resume.py  # 简历筛选
│       │       └── match.py   # 职位匹配
│       └── internal/          # 内部API
│           └── endpoints.py
│
├── tool-service/              # 工具服务
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py           # 服务入口
│       ├── config/
│       │   └── settings.py
│       ├── internal/         # 内部API
│       │   └── endpoints/
│       │       ├── browser.py # 浏览器API
│       │       └── llm.py     # LLM API
│       └── tools/            # 工具实现
│           ├── browser/      # 浏览器工具
│           │   ├── __init__.py
│           │   ├── browser_service.py  # 浏览器服务
│           │   └── exceptions.py       # 异常定义
│           ├── llm/          # LLM工具
│           │   ├── __init__.py
│           │   ├── base.py   # 基础类
│           │   ├── claude/   # Claude实现
│           │   │   ├── __init__.py
│           │   │   ├── service.py     # Claude服务
│           │   │   ├── auth_handler.py # 认证处理
│           │   │   └── selectors.py   # 页面选择器
│           │   └── factory.py # LLM工厂
│           └── common/       # 通用工具
│               ├── cookies_manager.py  # Cookie管理
│               └── utils.py  # 工具函数
│
├── common/                   # 公共代码
│   ├── __init__.py
│   ├── models.py            # 共享模型
│   ├── exceptions.py        # 异常定义
│   └── utils/              # 工具函数
│       ├── __init__.py
│       ├── datetime.py
│       └── validation.py
│
└── tests/                   # 测试代码
    ├── conftest.py         # 测试配置
    ├── api_gateway/        # API网关测试
    ├── orchestrator/       # 编排服务测试
    ├── scenarios/          # 场景服务测试
    └── tools/              # 工具服务测试
        ├── browser/        # 浏览器工具测试
        └── llm/            # LLM工具测试

# 配置文件示例
config/
├── development.yml        # 开发环境配置
├── production.yml        # 生产环境配置
└── test.yml             # 测试环境配置
```