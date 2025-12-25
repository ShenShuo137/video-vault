# AI助手配置指南 (ChatAnywhere)

## 📋 配置步骤

### 1. 获取ChatAnywhere API密钥

如果你已经有ChatAnywhere的API密钥，跳过此步骤。

**ChatAnywhere常见服务商：**
- API2D: https://api2d.com
- ChatAnywhere: https://chatanywhere.tech
- OpenAI-SB: https://openai-sb.com
- 其他兼容OpenAI格式的API服务

### 2. 配置.env文件

编辑项目根目录的`.env`文件，修改以下三个配置项：

```env
# AI大模型API配置 (ChatAnywhere)
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # 替换为你的API Key
LLM_API_BASE=https://api.chatanywhere.tech/v1             # 替换为你的API地址
LLM_MODEL=gpt-3.5-turbo                                   # 或 gpt-4
```

**配置说明：**

| 参数 | 说明 | 示例 |
|-----|------|------|
| `LLM_API_KEY` | API密钥，通常以`sk-`开头 | `sk-abc123...` |
| `LLM_API_BASE` | API服务地址，必须包含`/v1` | `https://api.chatanywhere.tech/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-3.5-turbo` (推荐), `gpt-4` |

**常见API Base地址：**
- ChatAnywhere: `https://api.chatanywhere.tech/v1`
- API2D: `https://openai.api2d.net/v1`
- OpenAI-SB: `https://api.openai-sb.com/v1`
- OpenAI官方: `https://api.openai.com/v1`

### 3. 重启后端服务

配置完成后，重启Flask后端以加载新配置：

```bash
# 如果后端正在运行，先停止（Ctrl+C）
# 然后重新启动
cd backend
python app.py
```

**预期输出：**
```
============================================================
Video Vault Backend API Server
============================================================
运行模式: 本地测试
AI Agent: 可用        <-- 这里应该显示"可用"
上传目录: D:\video-vault\backend\uploads
============================================================
```

如果显示`AI Agent: 不可用`，说明配置有问题。

---

## 🧪 测试AI助手

### 方法1: 通过Web界面测试（推荐）

1. 确保前后端都在运行
2. 访问：http://localhost:5173
3. 点击左侧菜单 **AI助手**
4. 输入测试问题，例如：
   - "有哪些高风险视频？"
   - "最近发现了哪些敏感信息？"
   - "给我生成一份安全审计报告"

### 方法2: 通过API测试

使用curl或Postman测试API接口：

```bash
# 测试AI对话
curl -X POST http://127.0.0.1:5000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请介绍一下你的功能"}'
```

**预期响应：**
```json
{
  "response": "您好！我是Video Vault的AI安全助手...",
  "timestamp": "2024-01-20T10:30:00"
}
```

### 方法3: 直接运行测试脚本

创建测试文件`test_ai_agent.py`：

```python
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from functions.ai_agent.agent import VideoVaultAgent

# 初始化AI Agent
agent = VideoVaultAgent()

# 测试对话
print("测试AI Agent...")
response = agent.chat("你好，请介绍一下你的功能")
print(f"\nAI回复:\n{response}\n")

# 测试工具调用
response = agent.chat("帮我列出所有高风险视频")
print(f"\nAI回复:\n{response}\n")
```

运行测试：
```bash
python test_ai_agent.py
```

---

## 💬 AI助手功能

AI助手可以帮你完成以下任务：

### 1. 查询审计日志
**示例问题：**
- "最近7天发现了哪些敏感信息？"
- "查询包含API密钥的检测记录"
- "视频ID为xxx的审计日志是什么？"

### 2. 查询视频状态
**示例问题：**
- "视频xxx的处理状态是什么？"
- "有多少个视频正在处理？"
- "显示所有已完成的视频"

### 3. 列出高风险视频
**示例问题：**
- "有哪些高风险视频？"
- "列出包含超过5个敏感信息的视频"
- "最危险的视频是哪些？"

### 4. 水印溯源（需要实现）
**示例问题：**
- "这个视频是谁下载的？"
- "提取视频xxx的水印信息"
- "追溯视频泄露者"

### 5. 生成安全报告
**示例问题：**
- "生成本周的安全审计报告"
- "给我一份最近30天的统计报告"
- "分析当前的安全风险"

---

## 🐛 常见问题

### Q1: AI Agent显示"不可用"

**可能原因：**
1. `.env`中未配置`LLM_API_KEY`
2. API密钥格式错误
3. API Base地址错误（缺少`/v1`）
4. openai库未安装

**解决方法：**
```bash
# 1. 检查.env配置
cat .env | grep LLM_

# 2. 确保openai库已安装
pip install openai

# 3. 测试API连接
python -c "from openai import OpenAI; client = OpenAI(api_key='你的key', base_url='你的base'); print(client.models.list())"
```

### Q2: AI回复报错 "API request failed"

**可能原因：**
- API密钥无效或已过期
- API额度用完
- 网络连接问题
- API服务不可用

**解决方法：**
1. 检查API密钥是否正确
2. 登录ChatAnywhere检查余额
3. 尝试ping API服务器
4. 查看后端控制台的详细错误信息

### Q3: AI助手不调用工具

**可能原因：**
- 模型不支持Function Calling（如某些gpt-3.5-turbo-0301）
- 问题表述不够明确

**解决方法：**
1. 使用支持Function Calling的模型：
   ```env
   LLM_MODEL=gpt-3.5-turbo-1106  # 或更新版本
   ```
2. 更明确地表述问题：
   - ❌ "看看有什么问题"
   - ✅ "列出所有高风险视频"

### Q4: 本地模式下AI助手查询不到数据

**说明：**
- 本地模式（`LOCAL_MODE=true`）不使用数据库
- AI助手需要从本地文件读取数据

**解决方法：**
确保已处理过视频，审计日志文件会保存在：
```
backend/uploads/output/<video_id>/audit_log.json
```

---

## 💰 成本估算

使用ChatAnywhere API的成本示例（以gpt-3.5-turbo为例）：

| 操作 | Token消耗 | 成本（约） |
|-----|---------|-----------|
| 简单问答 | 100-300 tokens | ¥0.001-0.003 |
| 调用工具查询 | 500-1000 tokens | ¥0.005-0.01 |
| 生成报告 | 1000-2000 tokens | ¥0.01-0.02 |

**月度估算：**
- 轻度使用（10次/天）：¥1-3/月
- 中度使用（50次/天）：¥5-15/月
- 重度使用（200次/天）：¥20-60/月

**建议：**
- 开发测试用`gpt-3.5-turbo`（便宜）
- 生产环境或演示用`gpt-4`（效果更好）

---

## 🔐 安全建议

1. **不要泄露API密钥**
   - 不要提交`.env`到Git
   - 项目已包含`.gitignore`规则

2. **设置使用限额**
   - 在ChatAnywhere后台设置每日/每月限额
   - 避免API密钥被滥用

3. **定期轮换密钥**
   - 每3-6个月更换一次API密钥
   - 旧密钥泄露后立即废弃

---

## 🎯 下一步

配置完成后，你可以：

1. ✅ 通过Web界面体验AI助手对话
2. ✅ 让AI助手帮你分析视频安全情况
3. ✅ 生成自动化的安全审计报告
4. ✅ 演示智能安全平台的完整功能

**祝使用愉快！** 🎉
