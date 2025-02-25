# intelligent-agent
# Agent系统使用说明

这是一个通用的智能Agent系统，可支持多种自动化场景，如简历筛选、电商运营、价格比较和银行账单查询等。

## 环境要求

- Python 3.8+
- Playwright (自动安装)
- FastAPI, Uvicorn, HTTPX等依赖包 (自动安装)

## 快速启动

1. 克隆此仓库，并进入项目目录:

```bash
git clone <repository-url>
cd intelligent-agent
```

2. 运行本地启动脚本:

```bash
python run_local.py
```

此命令将:
- 安装所有必要的依赖
- 安装Playwright和Chromium浏览器
- 启动所有服务（API网关、编排服务、场景服务和工具服务）

若只想启动特定服务，可以指定服务名称:

```bash
python run_local.py --services api-gateway tool
```

## 测试场景

系统预置了四个场景的测试脚本，在运行服务后可以选择测试:

### 信用卡账单查询

```bash
python test_credit_card.py
```

这将自动访问中信银行信用卡中心网站，查询账单金额。

### 简历筛选与评估

```bash
python test_hr_recruitment.py
```

访问招聘网站，提取求职者简历并根据职位要求进行评分排序。
注意：使用前需要在脚本中设置正确的登录凭证。

### 电商平台运营

```bash
python test_ecommerce.py
```

在多平台（Amazon、Temu、Shopee等）上管理电商账号，可执行产品列表查询、添加产品、回复客户等操作。
注意：使用前需要在脚本中设置正确的账号凭证和平台选择。

### 价格比较与购物车

```bash
python test_price_comparison.py
```

在多个平台（淘宝、京东、拼多多等）搜索产品并比较价格，找到最优选择并加入购物车。
注意：使用前需要在脚本中设置要搜索的产品和价格区间。

## 服务访问端口

- API网关: http://localhost:8000
- 编排服务: http://localhost:8001
- 场景服务: http://localhost:8002
- 工具服务: http://localhost:8003

## 自定义场景

系统设计支持自定义场景。要添加新场景，需要:

1. 在`scenario-service/src/scenarios/`中创建新的场景类
2. 在`orchestrator-service/src/workflows/`中创建对应的工作流类
3. 在`tool-service/src/tools/handlers/`中实现必要的处理器
4. 将新场景注册到`ScenarioRegistry`和`TaskOrchestrator`中

## 项目结构

```
intelligent-agent/
├── api-gateway/          # API网关服务
├── orchestrator-service/ # 任务编排服务
├── scenario-service/     # 场景定义服务
├── tool-service/         # 工具服务(浏览器、LLM等)
├── common/               # 公共组件
└── tests/                # 测试代码
```

## 注意事项

- 涉及登录的场景需要提供正确的账号凭证
- 首次登录可能需要手动完成验证码或安全校验
- 系统会在`./browser_data`目录保存cookies，便于后续登录
- 运行过程中请勿关闭自动打开的浏览器窗口
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