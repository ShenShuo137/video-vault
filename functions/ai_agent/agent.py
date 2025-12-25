"""
AI Agent 主模块
实现智能安全助手 - 充当首席安全官(CISO)角色
"""
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from openai import OpenAI
from shared.config import Config
from functions.ai_agent.tools import VideoVaultTools, TOOLS_SCHEMA


class VideoVaultAgent:
    """Video Vault AI Agent - 智能安全助手"""

    def __init__(self, api_key=None, api_base=None, model=None):
        """
        初始化AI Agent
        :param api_key: API密钥
        :param api_base: API基础URL
        :param model: 模型名称
        """
        self.api_key = api_key or Config.LLM_API_KEY
        self.api_base = api_base or Config.LLM_API_BASE
        self.model = model or Config.LLM_MODEL

        if not self.api_key:
            raise ValueError("需要配置LLM_API_KEY环境变量")

        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        self.tools = VideoVaultTools()

        # 系统提示词
        self.system_prompt = """你是Video Vault智能安全平台的AI助手，扮演企业首席安全官(CISO)的角色。

你的职责是：
1. 帮助用户查询视频中的敏感信息检测情况
2. 分析安全风险并提供建议
3. 协助溯源泄露视频的下载者
4. 生成安全审计报告

你可以使用以下工具：
- query_audit_logs: 查询审计日志
- get_video_status: 查询视频状态
- list_sensitive_videos: 列出高风险视频
- extract_watermark: 提取水印溯源
- get_security_report: 生成安全报告

回答风格：
- 专业、准确、简洁
- 使用中文回答
- 发现严重安全问题时要强调风险
- 提供可操作的建议
"""

        self.conversation_history = []

    def chat(self, user_message):
        """
        与用户对话
        :param user_message: 用户消息
        :return: AI回复
        """
        # 添加用户消息到历史
        if not self.conversation_history:
            self.conversation_history.append({
                "role": "system",
                "content": self.system_prompt
            })

        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # 调用大模型
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.conversation_history,
            tools=TOOLS_SCHEMA,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # 检查是否需要调用工具
        if message.tool_calls:
            # 处理工具调用
            self.conversation_history.append(message)

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"\n[调用工具] {function_name}({function_args})")

                # 执行工具函数
                function_result = self._execute_tool(function_name, function_args)

                # 添加工具结果到历史
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_result, ensure_ascii=False)
                })

            # 再次调用模型，让它根据工具结果生成回复
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history
            )

            message = response.choices[0].message

        # 添加助手回复到历史
        self.conversation_history.append({
            "role": "assistant",
            "content": message.content
        })

        return message.content

    def _execute_tool(self, function_name, function_args):
        """执行工具函数"""
        try:
            if function_name == "query_audit_logs":
                return self.tools.query_audit_logs(**function_args)
            elif function_name == "get_video_status":
                return self.tools.get_video_status(**function_args)
            elif function_name == "list_sensitive_videos":
                return self.tools.list_sensitive_videos(**function_args)
            elif function_name == "extract_watermark":
                return self.tools.extract_watermark(**function_args)
            elif function_name == "get_security_report":
                return self.tools.get_security_report(**function_args)
            else:
                return {"error": f"未知工具: {function_name}"}

        except Exception as e:
            return {"error": str(e)}

    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []


def main():
    """主函数 - 交互式测试"""
    print("=" * 60)
    print("Video Vault AI Agent - 智能安全助手")
    print("=" * 60)
    print("\n提示: 输入 'quit' 或 'exit' 退出")
    print("      输入 'reset' 重置对话\n")

    try:
        agent = VideoVaultAgent()
    except ValueError as e:
        print(f"\n❌ 初始化失败: {e}")
        print("\n请在.env文件中配置:")
        print("  LLM_API_KEY=your_api_key")
        print("  LLM_API_BASE=https://api.openai.com/v1")
        print("  LLM_MODEL=gpt-4")
        return

    print("✅ AI Agent已就绪!\n")

    # 示例问题
    print("示例问题:")
    print("  - 最近一周检测到了哪些敏感信息?")
    print("  - 有哪些高风险视频?")
    print("  - 生成安全报告")
    print()

    while True:
        try:
            user_input = input("您: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\n再见!")
                break

            if user_input.lower() == 'reset':
                agent.reset_conversation()
                print("\n✅ 对话已重置\n")
                continue

            # 获取AI回复
            response = agent.chat(user_input)
            print(f"\nAI: {response}\n")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")


if __name__ == '__main__':
    main()
