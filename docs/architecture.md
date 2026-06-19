# 小旅星 · 架构文档

## Workflow 数据流

```
Start(用户输入)
  │
  ├──► EXTRACT_XHS_URL ────► has_xhs_url: bool / xhs_url: str
  │                              │
  ├──► normalize_date ──────► travel_days: int
  │                              │
  └──► parse_destinations ──► destination_text: str / destination_count: int
                                 │
                                 ▼
                      recommend_top_pois (LLM)
                      → 为每个目的地推荐候选景点
                                 │
                                 ▼
                      GENERATE_ROUTE_FAST (LLM)
                      → 生成每日路线
                                 │
                                 ▼
                      IF-ELSE: has_xhs_url?
                        │            │
                       NO           YES
                        │            │
                        │            ▼
                        │    HTTP Request
                        │    → POST /parse-xhs
                        │            │
                        │            ▼
                        │    PARSE_XHS_BODY (Code)
                        │    → 抽取 success/title/content
                        │            │
                        │            ▼
                        │    XHS_CONTENT_EXTRACT (LLM)
                        │    → 提取避坑/交通/美食等洞察
                        │            │
                        │            ▼
                        │    GENERATE_TRAVEL_GUIDE (LLM)
                        │    → 合并路线 + 小红书增强
                        │            │
                        ▼            ▼
                      End(输出最终攻略)
```

## 节点设计原则

### 1. 代码节点负责确定性逻辑

- `normalize_date`：日期差值计算 → 强确定性，无需 LLM
- `parse_destinations`：文本分割和拼接 → 规则明确
- `EXTRACT_XHS_URL`：正则匹配 URL → 确定性高
- `PARSE_XHS_BODY`：JSON 解析 → 确定性高

### 2. LLM 节点负责非确定性推理

- `recommend_top_pois`：需要旅行知识和创意
- `GENERATE_ROUTE_FAST`：需要路线规划推理
- `XHS_CONTENT_EXTRACT`：需要自然语言理解
- `GENERATE_TRAVEL_GUIDE`：需要信息综合和内容生成

### 3. 条件分支实现优雅降级

小红书功能是可选的。没有链接时，Workflow 跳过 HTTP 请求和后续增强节点，直接输出基础路线——不会因为外部服务不可用而整体失败。

## 变量流转

| 变量名 | 来源节点 | 流向节点 |
|--------|----------|----------|
| `start_date` / `end_date` | Start | normalize_date |
| `destination` | Start | parse_destinations |
| `travel_style` | Start | recommend_top_pois, GENERATE_ROUTE_FAST |
| `pace` | Start | recommend_top_pois, GENERATE_ROUTE_FAST |
| `xhs_share_text` | Start | EXTRACT_XHS_URL |
| `travel_days` | normalize_date | recommend_top_pois, GENERATE_ROUTE_FAST |
| `destination_text` | parse_destinations | recommend_top_pois, GENERATE_ROUTE_FAST |
| `has_xhs_url` | EXTRACT_XHS_URL | IF-ELSE |
| `xhs_url` | EXTRACT_XHS_URL | HTTP Request |

## 扩展建议

- **知识库集成**：Workflow 已启用 `retriever_resource`，可关联目的地知识库提高推荐质量
- **多模型切换**：将 LLM 节点替换为 Claude、GPT-4 等，对比输出质量
- **记忆能力**：可添加 `conversation_variables` 实现多轮对话修正路线
- **图片识别**：启动 `file_upload` 功能，支持上传图片识别景点
