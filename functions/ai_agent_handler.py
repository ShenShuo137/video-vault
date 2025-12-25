"""
华为云FunctionGraph入口 - AI Agent函数
触发方式: HTTP触发器（通过API Gateway）
"""
import json
import os
import sys

sys.path.insert(0, '/opt/python')  # 依赖层路径
sys.path.insert(0, os.path.dirname(__file__))

from functions.ai_agent.agent_serverless import VideoVaultAgentServerless
from shared.config import Config


# 初始化AI Agent（全局变量，复用实例）
ai_agent = None


def handler(event, context):
    """
    FunctionGraph Handler入口函数

    event结构（HTTP触发器）:
    {
        "body": "{\"message\": \"查询最近的审计日志\", \"action\": \"chat\"}",
        "httpMethod": "POST",
        "headers": {...},
        "queryStringParameters": {...}
    }

    :param event: HTTP请求事件
    :param context: FunctionGraph上下文
    :return: HTTP响应
    """
    logger = context.getLogger()
    logger.info(f"收到AI Agent请求: {json.dumps(event)}")

    try:
        # 解析请求体
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        action = body.get('action', 'chat')
        message = body.get('message', '')

        if not message and action == 'chat':
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "error": "消息不能为空"
                }, ensure_ascii=False)
            }

        # 初始化AI Agent（懒加载）
        global ai_agent
        if ai_agent is None:
            try:
                ai_agent = VideoVaultAgentServerless(
                    api_key=Config.LLM_API_KEY,
                    api_base=Config.LLM_API_BASE,
                    model=Config.LLM_MODEL
                )
                logger.info("AI Agent (Serverless) 初始化成功")
            except Exception as e:
                logger.error(f"AI Agent初始化失败: {str(e)}")
                return {
                    "statusCode": 503,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({
                        "error": f"AI Agent未配置: {str(e)}",
                        "hint": "请检查环境变量 LLM_API_KEY, LLM_API_BASE, LLM_MODEL"
                    }, ensure_ascii=False)
                }

        # 处理不同动作
        if action == 'chat':
            # 对话
            response_text = ai_agent.chat(message)
            logger.info(f"AI回复: {response_text[:100]}...")

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "response": response_text,
                    "timestamp": context.getLogger().request_id
                }, ensure_ascii=False)
            }

        elif action == 'reset':
            # 重置对话
            ai_agent.reset_conversation()
            logger.info("对话已重置")

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "message": "对话已重置"
                }, ensure_ascii=False)
            }

        else:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "error": f"不支持的动作: {action}",
                    "supported_actions": ["chat", "reset"]
                }, ensure_ascii=False)
            }

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": f"请求格式错误: {str(e)}"
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"AI Agent处理失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e),
                "type": type(e).__name__
            }, ensure_ascii=False)
        }
