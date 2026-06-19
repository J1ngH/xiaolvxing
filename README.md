# 小旅星 · AI 智能旅游规划助手

[![Dify](https://img.shields.io/badge/Dify-Workflow-blue?logo=dify)](https://dify.ai)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20V4-green)](https://deepseek.com)
[![Streamlit](https://img.shields.io/badge/Demo-Streamlit-red?logo=streamlit)](https://xiaolvxing.streamlit.app)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 基于 Dify Workflow + DeepSeek 大模型的智能旅行路线规划工具，支持多目的地行程生成 + 小红书笔记增强。

## 🎯 项目概述

输入目的地、日期、旅行风格和节奏，自动生成一份完整的多日旅行攻略，包括每日路线、景点推荐、停留时长等。如果提供小红书分享链接，还会自动抓取真实用户的避坑建议、交通贴士、美食推荐等内容，在原路线基础上进行增强。

### 🌐 在线体验

**👉 [点击立即体验](https://xiaolvxing.streamlit.app)**（无需注册，打开即用）

### Demo 展示

<!-- TODO: 替换为你的截图/GIF -->
![Demo](assets/demo.png)

## 🏗️ Workflow 架构

```
用户输入
  ├─ destination（目的地）
  ├─ start_date / end_date（日期范围）
  ├─ travel_style（旅行风格）
  ├─ pace（旅行节奏）
  └─ xhs_share_text（小红书链接，可选）
       │
       ▼
┌──────────────────────────────────────────┐
│  ① normalize_date        计算游玩天数      │
│  ② parse_destinations    解析多目的地      │
│  ③ recommend_top_pois    LLM 推荐景点      │
│  ④ GENERATE_ROUTE_FAST   LLM 生成路线      │
│  ⑤ 条件分支                                │
│     ├─ 无小红书链接 → 直接输出             │
│     └─ 有小红书链接 → HTTP请求抓取          │
│          │                                 │
│          ├─ PARSE_XHS_BODY      解析响应    │
│          ├─ XHS_CONTENT_EXTRACT 提取信息   │
│          └─ GENERATE_TRAVEL_GUIDE 增强路线 │
│                     │                     │
│                     ▼                     │
│              输出最终攻略                   │
└──────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 编排平台 | [Dify](https://dify.ai) Workflow DSL |
| 大模型 | DeepSeek V4 Pro（通过 Dify 插件市场接入） |
| 代码节点 | Python 3（日期计算、文本解析、JSON 提取） |
| 外部集成 | 小红书内容解析 API（HTTP Request 节点） |
| 条件分支 | IF-ELSE 节点（有无小红书链接） |

### 节点详解

| 节点 | 类型 | 功能 |
|------|------|------|
| `normalize_date` | Code (Python) | 计算起止日期之间的游玩天数 |
| `parse_destinations` | Code (Python) | 解析用户输入的多目的地（支持逗号、中文逗号、换行分隔） |
| `recommend_top_pois` | LLM | 根据旅行风格为每个目的地推荐最多 5 个景点 |
| `GENERATE_ROUTE_FAST` | LLM | 根据节奏生成每日路线（特种兵 / 适中 / 休闲） |
| `EXTRACT_XHS_URL` | Code (Python) | 从用户粘贴的分享文本中提取小红书链接 |
| `PARSE_XHS_BODY` | Code (Python) | 解析小红书抓取服务的 HTTP 响应 |
| `XHS_CONTENT_EXTRACT` | LLM | 从小红书正文提取避坑、交通、美食等信息 |
| `GENERATE_TRAVEL_GUIDE` | LLM | 在小红书信息基础上增强原路线 |

## 🚀 如何运行

### 方式一：在线体验

**👉 [xiaolvxing.streamlit.app](https://xiaolvxing.streamlit.app)**

打开链接 → 输入目的地 → 点击生成 → 秒出攻略。无需安装任何东西。

### 方式二：本地 Streamlit 运行

```bash
# 1. 克隆仓库
git clone https://github.com/J1ngH/xiaolvxing.git
cd xiaolvxing

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置 DeepSeek API Key
# 在 https://platform.deepseek.com/api_keys 获取
export DEEPSEEK_API_KEY=sk-your-key-here

# 4. 启动应用
streamlit run app.py
# → 打开 http://localhost:8501
```

### 方式三：Dify 导入（展示 Workflow 编排能力）

1. 注册 [Dify](https://cloud.dify.ai) 账号（或本地部署 Dify）
2. 在 Dify 中配置 DeepSeek 模型提供商，填入你的 API Key
3. Dify 控制台 → 创建应用 → 选择 Workflow → 导入 DSL → 选择 `workflow.yml`
4. （可选）部署小红书内容解析服务，或跳过增强功能直接使用

### 示例输入

```
目的地：成都、九寨沟
开始日期：2026-07-01
结束日期：2026-07-05
旅行风格：美食优先
旅行节奏：适中
小红书分享文本：（可选）https://www.xiaohongshu.com/explore/xxxxx
```

### 示例输出

```json
{
  "itinerary": [
    {
      "day": 1,
      "destination": "成都",
      "theme": "成都美食初探",
      "route": [
        {
          "name": "宽窄巷子",
          "time_period": "上午",
          "stay_hours": 2,
          "reason": "成都文化地标，适合上午游览",
          "xhs_tips": [
            { "type": "避坑提示", "content": "避开周末人流高峰" }
          ]
        }
      ],
      "summary_tips": ["锦里和宽窄巷子可安排在同一天"]
    }
  ]
}
```

## 📁 项目结构

```
xiaolvxing/
├── README.md                # 项目说明
├── app.py                   # Streamlit 在线 Demo（可独立运行）
├── workflow.yml             # Dify Workflow DSL 导出文件
├── requirements.txt         # Python 依赖
├── .streamlit/
│   └── config.toml          # Streamlit 配置
├── assets/
│   └── demo.png             # 运行截图
└── docs/
    └── architecture.md      # 详细架构文档
```

## 🔧 自定义配置

### 修改 LLM 模型

在 Dify 中导入后，可在 LLM 节点中将模型替换为 GPT-4、Claude 等任意支持的模型。

### 配置小红书解析服务

Workflow 中的 HTTP Request 节点默认调用 `http://host.docker.internal:8000/parse-xhs`，这是本地部署的服务地址。导入后你可以：

- **方案 A**：部署自己的小红书解析服务，修改 URL 指向你的服务
- **方案 B**：不提供小红书链接，Workflow 会自动跳过增强步骤，直接输出基础路线

### 添加知识库

Workflow 已启用 `retriever_resource`，可在 Dify 中关联旅行知识库来增强推荐效果。

## 📝 设计思路

1. **Pipeline 架构**：每个节点职责单一，输入输出明确，便于调试和复用
2. **容错设计**：小红书抓取失败不影响主流程，通过条件分支优雅降级
3. **结构化输出**：LLM 节点均启用 Structured Output，确保输出格式稳定可解析
4. **去重 & 约束**：日期计算、文本解析由代码节点完成，减少 LLM 幻觉风险

## 📄 License

MIT © [J1ngH](https://github.com/J1ngH)
