"""
小旅星 · AI 智能旅游规划助手
==============================
基于 DeepSeek 大模型的多目的地旅行路线生成 + 小红书攻略增强
Dify Workflow 的独立 Streamlit 实现

线上体验: https://xiaolvxing.streamlit.app
GitHub: https://github.com/J1ngH/xiaolvxing
"""

import streamlit as st
import openai
import json
import re
import os
from datetime import datetime
from typing import Optional

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="小旅星 · AI 旅游规划",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CSS 样式
# ============================================================
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0 0.5rem 0;
    }
    .main-header h1 {
        font-size: 2.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .subtitle {
        text-align: center;
        color: #888;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }
    .step-container {
        border-left: 3px solid #667eea;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
        border-radius: 0 8px 8px 0;
    }
    .day-card {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    .day-card h3 {
        margin-top: 0;
        color: #667eea;
    }
    .poi-item {
        display: flex;
        align-items: flex-start;
        gap: 0.8rem;
        padding: 0.6rem 0;
        border-bottom: 1px dashed #e0e0e0;
    }
    .poi-item:last-child { border-bottom: none; }
    .time-badge {
        background: #667eea;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        white-space: nowrap;
    }
    .tip-badge {
        background: #fff3cd;
        color: #856404;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.78rem;
        margin: 2px 2px;
        display: inline-block;
    }
    .footer {
        text-align: center;
        color: #aaa;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# 工具函数（复刻 Dify Workflow 的 Code 节点）
# ============================================================


def normalize_date(start_date: str, end_date: str) -> int:
    """计算游玩天数（复刻 normalize_date 节点）"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    return (end_dt - start_dt).days + 1


def parse_destinations(destination: str) -> tuple[str, int]:
    """解析多目的地（复刻 parse_destinations 节点）"""
    text = destination.replace("，", ",").replace("、", ",").replace("\n", ",")
    destination_list = [item.strip() for item in text.split(",") if item.strip()]
    return "、".join(destination_list), len(destination_list)


def extract_xhs_url(xhs_share_text: str) -> tuple[str, bool]:
    """从小红书分享文本中提取链接（复刻 EXTRACT_XHS_URL 节点）"""
    if not xhs_share_text:
        return "", False
    pattern = r"https?://[^\s，。！？]+"
    match = re.search(pattern, xhs_share_text)
    if not match:
        return "", False
    return match.group(0).strip(), True


# ============================================================
# LLM 调用（复刻 Dify Workflow 的 LLM 节点）
# ============================================================


def get_api_key() -> str:
    """获取 DeepSeek API Key（先查 Streamlit Secrets，再查环境变量）"""
    # Streamlit Cloud: 在 Secrets 中设置 DEEPSEEK_API_KEY = "sk-xxx"
    try:
        key = st.secrets["DEEPSEEK_API_KEY"]
        if key and key != "sk-your-api-key-here":
            return key
    except Exception:
        pass
    # 本地运行：环境变量
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key:
        return key
    return ""


def get_client() -> openai.OpenAI:
    """获取 DeepSeek API 客户端"""
    api_key = get_api_key()
    if not api_key:
        st.error("❌ 未配置 DeepSeek API Key！请在 Streamlit Cloud Secrets 中设置 `DEEPSEEK_API_KEY = \"sk-xxx\"`")
        st.stop()
    return openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def call_llm(system_prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """调用 DeepSeek LLM"""
    client = get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": system_prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def recommend_top_pois(
    destination_text: str,
    travel_style: str,
    travel_days: int,
    pace: str,
) -> dict:
    """推荐景点（复刻 recommend_top_pois 节点）"""
    prompt = f"""你是一位专业旅游顾问。

输入：
旅行地点：{destination_text}
旅游风格：{travel_style}
旅行天数：{travel_days}
旅行节奏：{pace}

任务：
为每个目的地推荐最多5个候选地点。

推荐规则：
- 大众打卡：地标景点、热门商圈、经典路线
- 自然景色：山川、湖泊、海边、自然风光
- 美食优先：夜市、美食街、特色餐饮聚集区
- 文化历史：古城、博物馆、历史街区、文化遗产
- 小众探索：游客较少但评价较高的地点

限制：
- 每个目的地最多5个POI
- reason不超过25字
- suggested_stay_hours只能是1、2、3
- best_time只能是上午、下午、晚上

只输出合法JSON，不要Markdown，不要解释，不要代码块。

输出格式：
{{
  "destinations": [
    {{
      "destination": "城市名称",
      "recommended_pois": [
        {{
          "name": "景点名称",
          "type": "景点",
          "reason": "推荐原因",
          "suggested_stay_hours": 2,
          "best_time": "上午"
        }}
      ]
    }}
  ]
}}"""
    result = call_llm(prompt, temperature=0.7)
    return _parse_json(result)


def generate_route_fast(
    destination_text: str,
    travel_days: int,
    travel_style: str,
    pace: str,
    pois_json: str,
) -> dict:
    """生成路线（复刻 GENERATE_ROUTE_FAST 节点）"""
    prompt = f"""你是一位专业旅游路线规划师。

输入：
旅行地点：{destination_text}
旅行天数：{travel_days}
旅游风格：{travel_style}
旅行节奏：{pace}
候选景点：{pois_json}

任务：
根据候选景点生成每日旅行路线。

## 硬性约束（违反即错误）
- **必须**生成恰好 {travel_days} 天的路线，一天都不能少
- 如果 {travel_days} 天排不满候选景点，最后几天可以安排自由探索、美食打卡等灵活行程
- 但无论如何，itinerary 数组长度必须等于 {travel_days}

规划规则：
- 每天最多3个地点
- 特种兵：每天3个地点
- 适中：每天2-3个地点
- 休闲：每天1-2个地点
- 同一天尽量安排顺路地点
- 夜市、美食街优先安排晚上
- 热门景点优先安排上午
- 不要重复安排同一地点

内容限制：
- theme不超过12字
- reason不超过25字
- summary_tips最多2条，每条不超过25字
- xhs_tips固定输出空数组 []

只输出合法JSON，不要Markdown，不要解释，不要代码块，不要<think>。

输出格式：
{{
  "itinerary": [
    {{
      "day": 1,
      "destination": "城市名称",
      "theme": "当天主题",
      "route": [
        {{
          "name": "景点名称",
          "time_period": "上午",
          "stay_hours": 2,
          "reason": "安排原因",
          "xhs_tips": []
        }}
      ],
      "summary_tips": []
    }}
  ]
}}

再次强调：itinerary 数组长度必须等于 {travel_days}，一天不能少。"""
    result = call_llm(prompt, temperature=0.7)
    return _parse_json(result)


def generate_travel_guide(base_route_json: str, xhs_insights_json: str) -> dict:
    """小红书增强路线（复刻 GENERATE_TRAVEL_GUIDE 节点）"""
    prompt = f"""## 角色

你是旅行攻略增强助手。

## 输入

基础路线 JSON：
{base_route_json}

小红书提取信息 JSON：
{xhs_insights_json}

## 任务

在不改变原路线结构的前提下，用小红书内容增强路线。

## 增强范围

仅允许补充：

1. 避坑提示
2. 交通建议
3. 餐饮推荐
4. 费用信息
5. 景点不推荐原因
6. 最佳游玩时间
7. 路线顺序建议
8. 住宿建议

## 规则

1. 保留原 itinerary 结构
2. 保留 day 字段
3. 保留 destination 字段
4. 保留 theme 字段
5. 保留 route 字段
6. 保留景点顺序
7. 不允许删除景点
8. 不允许新增景点
9. 不允许修改停留时间
10. 不允许修改天数
11. 只允许补充 route[].xhs_tips
12. 只允许补充 summary_tips
13. 如果小红书解析失败，直接返回基础路线 JSON
14. 不要重新规划路线
15. 不要编造小红书没有的信息

## 输出格式

{{
  "itinerary": [
    {{
      "day": 1,
      "destination": "城市名称",
      "theme": "当天主题",
      "route": [
        {{
          "name": "景点名称",
          "time_period": "上午",
          "stay_hours": 2,
          "reason": "安排原因",
          "xhs_tips": [
            {{
              "type": "避坑提示",
              "content": "具体内容"
            }}
          ]
        }}
      ],
      "summary_tips": [
        "整体补充建议"
      ]
    }}
  ]
}}

## 输出要求

只能输出合法 JSON。
禁止 Markdown。
禁止解释文字。
禁止代码块。
禁止输出 <think> 或任何推理过程。
禁止在 JSON 前后添加任何内容。
所有字段名必须使用英文双引号。
所有字符串必须使用英文双引号。"""
    result = call_llm(prompt, temperature=0.4, max_tokens=3072)
    return _parse_json(result)


def extract_xhs_insights(title: str, content: str, failed_reason: str) -> dict:
    """从小红书内容提取有用信息（复刻 XHS_CONTENT_EXTRACT 节点）"""
    prompt = f"""## 角色
你是旅行笔记信息提取助手。

## 输入
失败原因：{failed_reason}

小红书标题：{title}

小红书正文：{content}

## 任务
从小红书正文中提取可用于补充旅行攻略的信息。

## 提取类型
请重点提取以下信息：
1. 避坑提示
2. 交通建议
3. 餐饮推荐
4. 费用信息
5. 景点推荐
6. 景点不推荐原因
7. 最佳游玩时间
8. 住宿建议
9. 路线顺序建议

## 规则
1. 只提取正文中明确出现的信息
2. 不要编造正文没有的信息
3. 最多提取 12 条
4. 如果解析状态为 false，直接返回 failed
5. related_poi 填具体景点；无法确定景点时填城市名称
6. 只输出合法 JSON
7. 禁止输出 Markdown
8. 禁止输出解释文字
9. 禁止输出 <think> 或任何推理过程

## 输出格式
{{
  "fetch_status": "success",
  "useful_insights": [
    {{
      "related_poi": "相关景点或城市",
      "type": "避坑提示/交通建议/餐饮推荐/费用信息/景点推荐/景点不推荐原因/最佳游玩时间/住宿建议/路线顺序建议",
      "content": "具体信息"
    }}
  ],
  "failed_reason": ""
}}

## 失败输出格式
{{
  "fetch_status": "failed",
  "useful_insights": [],
  "failed_reason": "失败原因"
}}"""
    result = call_llm(prompt, temperature=0.2, max_tokens=2048)
    return _parse_json(result)


def _parse_json(text: str) -> dict:
    """尽量从 LLM 输出中提取 JSON"""
    if not text:
        return {}
    text = text.strip()
    # 去掉可能的 markdown 代码块
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    # 去掉 <think> 标签
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试用正则提取第一个 JSON 对象
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}


# ============================================================
# 小红书内容抓取（模拟原 Workflow 的 HTTP Request 节点）
# ============================================================


def fetch_xhs_content(xhs_url: str) -> dict:
    """
    尝试抓取小红书页面内容。
    注意：小红书有反爬机制，通常需要专用解析服务。
    在 Demo 中，如果抓取失败，工作流会自动跳过增强步骤（优雅降级）。
    """
    try:
        import urllib.request

        req = urllib.request.Request(
            xhs_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # 尝试从 HTML 中提取标题和描述
        title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # 提取 meta description
        desc_match = re.search(
            r'<meta[^>]*name="description"[^>]*content="([^"]*)"',
            html,
            re.IGNORECASE,
        )
        content = desc_match.group(1) if desc_match else ""

        if title or content:
            return {
                "success": True,
                "title": title[:200],
                "content": content[:3000],
                "source_url": xhs_url,
                "final_url": xhs_url,
                "failed_reason": "",
            }
        else:
            return {
                "success": False,
                "title": "",
                "content": "",
                "source_url": xhs_url,
                "final_url": xhs_url,
                "failed_reason": "页面内容为空或格式不支持",
            }
    except Exception as e:
        return {
            "success": False,
            "title": "",
            "content": "",
            "source_url": xhs_url,
            "final_url": xhs_url,
            "failed_reason": str(e)[:200],
        }


# ============================================================
# 主工作流
# ============================================================


def run_workflow(
    destination: str,
    start_date: str,
    end_date: str,
    travel_style: str,
    pace: str,
    xhs_share_text: str = "",
) -> dict:
    """
    执行完整的小旅星 Workflow。
    与 Dify Workflow 的图结构一一对应。
    """
    steps = {}  # 记录每个节点的输出，用于展示过程

    # ---- Step 1: 计算游玩天数 ----
    travel_days = normalize_date(start_date, end_date)
    steps["📅 计算游玩天数"] = f"{start_date} → {end_date}，共 **{travel_days}** 天"

    # ---- Step 2: 解析目的地 ----
    destination_text, destination_count = parse_destinations(destination)
    steps["📍 解析目的地"] = f"识别到 **{destination_count}** 个目的地：{destination_text}"

    # ---- Step 3: 提取小红书链接 ----
    xhs_url, has_xhs_url = extract_xhs_url(xhs_share_text)
    if has_xhs_url:
        steps["🔗 提取小红书链接"] = f"✅ 检测到链接：{xhs_url[:60]}..."
    else:
        steps["🔗 提取小红书链接"] = "未提供小红书链接，将跳过增强步骤"

    # ---- Step 4: AI 推荐景点 ----
    st.session_state["progress_text"] = "🤖 正在分析目的地，推荐候选景点..."
    pois_result = recommend_top_pois(destination_text, travel_style, travel_days, pace)
    poi_count = sum(
        len(d.get("recommended_pois", [])) for d in pois_result.get("destinations", [])
    )
    steps["🤖 AI 推荐景点"] = f"为 {len(pois_result.get('destinations', []))} 个目的地推荐了 **{poi_count}** 个候选景点"

    # ---- Step 5: AI 生成路线 ----
    st.session_state["progress_text"] = "🗺️ 正在规划每日旅行路线..."
    route_result = generate_route_fast(
        destination_text, travel_days, travel_style, pace, json.dumps(pois_result, ensure_ascii=False)
    )
    day_count = len(route_result.get("itinerary", []))

    # 兜底：如果 LLM 没生成足够天数，重试一次
    if day_count < travel_days:
        st.session_state["progress_text"] = "🗺️ 路线天数不足，正在补充规划..."
        route_result = generate_route_fast(
            destination_text, travel_days, travel_style, pace, json.dumps(pois_result, ensure_ascii=False)
        )
        day_count = len(route_result.get("itinerary", []))

    steps["🗺️ AI 生成路线"] = f"已生成 **{day_count}** 天行程"

    # ---- Step 6: 小红书增强（条件分支） ----
    if has_xhs_url:
        st.session_state["progress_text"] = "📕 正在抓取小红书内容..."
        xhs_data = fetch_xhs_content(xhs_url)

        if xhs_data["success"]:
            steps["📕 小红书抓取"] = f"✅ 成功获取笔记「{xhs_data['title'][:40]}...」"

            st.session_state["progress_text"] = "🔍 正在提取有用信息..."
            insights = extract_xhs_insights(
                xhs_data["title"], xhs_data["content"], xhs_data.get("failed_reason", "")
            )
            insight_count = len(insights.get("useful_insights", []))
            steps["🔍 信息提取"] = f"提取到 **{insight_count}** 条有用洞察"

            st.session_state["progress_text"] = "✨ 正在用小红书内容增强路线..."
            final_result = generate_travel_guide(
                json.dumps(route_result, ensure_ascii=False),
                json.dumps(insights, ensure_ascii=False),
            )
            steps["✨ 路线增强"] = "路线已用小红书真实攻略增强"
        else:
            steps["📕 小红书抓取"] = f"⚠️ 抓取失败（{xhs_data['failed_reason'][:50]}...），使用基础路线"
            final_result = route_result
    else:
        final_result = route_result

    steps["✅ 完成"] = "攻略生成完毕！"

    return {"itinerary": final_result.get("itinerary", []), "steps": steps}


# ============================================================
# UI 渲染
# ============================================================

# --- 头部 ---
st.markdown(
    '<div class="main-header"><h1>✈️ 小旅星 · AI 智能旅游规划</h1></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">输入目的地和偏好，秒级生成完整旅行攻略 · Powered by DeepSeek</div>',
    unsafe_allow_html=True,
)

# --- 输入区 ---
col1, col2, col3 = st.columns(3)

with col1:
    destination = st.text_input(
        "🌍 目的地",
        placeholder="例：成都、九寨沟",
        help="多个目的地用逗号分隔",
    )
    travel_style = st.selectbox(
        "🎯 旅行风格",
        ["大众打卡", "自然景色", "美食优先", "文化历史", "小众探索"],
    )

with col2:
    start_date = st.date_input("📅 出发日期", value=datetime.now())
    pace = st.selectbox("🏃 旅行节奏", ["适中", "特种兵", "休闲"])

with col3:
    end_date = st.date_input("📅 结束日期", value=datetime.now())
    xhs_share_text = st.text_area(
        "📕 小红书分享文本（可选）",
        placeholder="粘贴小红书分享文案，自动提取链接并增强攻略...",
        height=100,
    )

# --- 生成按钮 ---
st.markdown("<br>", unsafe_allow_html=True)
center_col = st.columns([1, 2, 1])[1]
with center_col:
    generate_btn = st.button(
        "🚀 生成旅行攻略",
        type="primary",
        use_container_width=True,
        disabled=not destination,
    )

# --- 结果区 ---
if generate_btn and destination:
    # 校验日期
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    if end_date < start_date:
        st.error("结束日期不能早于出发日期")
        st.stop()

    # 初始化进度
    if "progress_text" not in st.session_state:
        st.session_state["progress_text"] = ""

    progress_placeholder = st.empty()
    progress_bar = st.progress(0, text="")

    # 模拟进度（因为 LLM 调用是同步的）
    progress_steps = [
        (0.1, "📅 正在计算游玩天数..."),
        (0.2, "📍 正在解析目的地..."),
        (0.3, "🤖 正在 AI 推荐景点..."),
        (0.5, "🗺️ 正在规划每日路线..."),
        (0.75, "📕 正在处理小红书内容..." if xhs_share_text.strip() else "📕 跳过小红书增强..."),
        (0.9, "✨ 正在整理最终攻略..."),
    ]

    for pct, text in progress_steps:
        progress_bar.progress(pct, text=text)

    # ---- 执行工作流 ----
    with st.spinner("AI 正在为你规划旅行..."):
        result = run_workflow(
            destination=destination,
            start_date=start_str,
            end_date=end_str,
            travel_style=travel_style,
            pace=pace,
            xhs_share_text=xhs_share_text,
        )

    progress_bar.progress(1.0, text="✅ 攻略生成完毕！")
    progress_placeholder.empty()

    # ---- 展示流程步骤 ----
    st.markdown("### 🔄 处理流程")
    for label, detail in result["steps"].items():
        st.markdown(
            f'<div class="step-container"><strong>{label}</strong>：{detail}</div>',
            unsafe_allow_html=True,
        )

    # ---- 展示最终攻略 ----
    st.markdown("---")
    st.markdown("## 📋 完整旅行攻略")

    itinerary = result["itinerary"]
    if not itinerary:
        st.warning("未能生成路线，请检查输入后重试")
        st.stop()

    # 全天概览
    tabs = st.tabs(
        [f"Day {day.get('day', i + 1)}" for i, day in enumerate(itinerary)]
    )

    for i, (tab, day) in enumerate(zip(tabs, itinerary)):
        with tab:
            st.markdown(
                f"""
            <div class="day-card">
                <h3>📌 第 {day.get('day', i + 1)} 天：{day.get('theme', '探索日')}</h3>
                <p style="color:#666;margin-bottom:1rem;">📍 {day.get('destination', '')}</p>
            """,
                unsafe_allow_html=True,
            )

            for poi in day.get("route", []):
                time_period = poi.get("time_period", "")
                st.markdown(
                    f"""
                <div class="poi-item">
                    <span class="time-badge">{time_period}</span>
                    <div style="flex:1;">
                        <strong>{poi.get('name', '景点')}</strong>
                        <span style="color:#888;font-size:0.85rem;"> · 约{poi.get('stay_hours', 2)}小时</span>
                        <p style="color:#666;font-size:0.9rem;margin:4px 0;">{poi.get('reason', '')}</p>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # 显示小红书 tips
                for tip in poi.get("xhs_tips", []):
                    st.markdown(
                        f'<span class="tip-badge">💡 {tip.get("type", "提示")}：{tip.get("content", "")}</span>',
                        unsafe_allow_html=True,
                    )

            # 每日总结
            for tip in day.get("summary_tips", []):
                st.markdown(
                    f'<div style="background:#e8f4fd;padding:8px 12px;border-radius:6px;margin:4px 0;font-size:0.9rem;">📝 {tip}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

    # ---- JSON 导出 ----
    st.markdown("---")
    st.markdown("### 📥 导出结果")

    col_json, col_download = st.columns([2, 1])
    with col_json:
        with st.expander("查看 JSON 数据"):
            st.json(result["itinerary"])
    with col_download:
        json_str = json.dumps(
            {"itinerary": itinerary}, ensure_ascii=False, indent=2
        )
        st.download_button(
            label="📥 下载攻略 JSON",
            data=json_str,
            file_name=f"travel_plan_{start_str}.json",
            mime="application/json",
        )

# --- 当没有输入时 ---
elif not generate_btn:
    st.markdown("---")
    st.info("👆 请在上方输入旅行信息，然后点击「生成旅行攻略」按钮")

# --- 页脚 ---
st.markdown(
    """
<div class="footer">
    <p>小旅星 · AI 智能旅游规划助手 | Powered by DeepSeek + Dify + Streamlit</p>
    <p>
        <a href="https://github.com/J1ngH/xiaolvxing" target="_blank">📂 GitHub</a> ·
        <a href="https://dify.ai" target="_blank">🔗 Dify</a> ·
        <a href="https://deepseek.com" target="_blank">🤖 DeepSeek</a>
    </p>
</div>
""",
    unsafe_allow_html=True,
)
