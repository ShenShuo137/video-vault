/**
 * 华为云FunctionGraph SDK调用工具
 * 用于直接调用云函数，无需API网关
 */
import * as FunctionGraph from '@huaweicloud/huaweicloud-sdk-functiongraph';

const ak = import.meta.env.VITE_HUAWEI_CLOUD_AK;
const sk = import.meta.env.VITE_HUAWEI_CLOUD_SK;
const projectId = import.meta.env.VITE_FUNCTION_PROJECT_ID;
const region = import.meta.env.VITE_HUAWEI_CLOUD_REGION || 'cn-north-4';

/**
 * 创建FunctionGraph客户端
 */
function createClient() {
  if (!ak || !sk || !projectId) {
    throw new Error('缺少必要的环境变量配置：VITE_HUAWEI_CLOUD_AK, VITE_HUAWEI_CLOUD_SK, VITE_FUNCTION_PROJECT_ID');
  }

  const credentials = new FunctionGraph.BasicCredentials()
    .withAk(ak)
    .withSk(sk)
    .withProjectId(projectId);

  const client = FunctionGraph.FunctionGraphClient.newBuilder()
    .withCredential(credentials)
    .withEndpoint(`https://functiongraph.${region}.myhuaweicloud.com`)
    .build();

  return client;
}

/**
 * 调用AI Agent函数
 * @param {string} action - 'chat' 或 'reset'
 * @param {string} message - 用户消息
 * @returns {Promise<object>} - 函数返回结果
 */
export async function invokeAIAgent(action, message = '') {
  try {
    const client = createClient();

    const request = new FunctionGraph.InvokeFunctionRequest();

    // 设置函数URN
    request.functionUrn = `urn:fss:${region}:${projectId}:function:default:video-vault-ai-agent:latest`;

    // 设置请求体
    const payload = {
      action: action,
      message: message
    };

    request.body = payload;

    console.log('调用AI Agent函数:', { action, message: message.substring(0, 50) });

    // 调用函数
    const response = await client.invokeFunction(request);

    // 解析返回结果
    // response.result 是字符串，需要解析
    let result = response.result;
    console.log('原始响应:', result);

    if (typeof result === 'string') {
      result = JSON.parse(result);
    }

    // result 是 {statusCode: 200, body: "...", headers: {...}}
    // body 也是字符串，需要再次解析
    if (result.body && typeof result.body === 'string') {
      result.body = JSON.parse(result.body);
    }

    console.log('解析后结果:', result);

    // 检查状态码
    if (result.statusCode !== 200) {
      throw new Error(result.body?.error || '函数执行失败');
    }

    // 返回实际数据
    return result.body;
  } catch (error) {
    console.error('调用AI Agent函数失败:', error);

    // 提供更友好的错误信息
    if (error.message.includes('缺少必要的环境变量')) {
      throw new Error('环境变量配置不完整，请检查.env文件');
    } else if (error.message.includes('404')) {
      throw new Error('AI Agent函数不存在，请先在华为云创建函数');
    } else if (error.message.includes('403')) {
      throw new Error('权限不足，请检查AK/SK是否正确');
    } else {
      throw new Error(`函数调用失败: ${error.message}`);
    }
  }
}
