# 华为云FunctionGraph依赖层完全指南

## 🎯 华为云FunctionGraph依赖层支持

### ✅ 是的，华为云FunctionGraph支持依赖层（Layer）！

**官方文档：**
- 支持自定义依赖层
- 可以打包Python库、二进制文件、配置文件等
- 可以跨函数共享依赖层

---

## 📊 依赖层限制

| 限制项 | Python 3.9/3.11 | Node.js |
|-------|----------------|---------|
| **单层大小** | 100MB（压缩后） | 100MB |
| **层的数量** | 最多5层/函数 | 最多5层/函数 |
| **总大小** | 500MB（所有层+函数包解压后） | 500MB |
| **运行时** | /opt/python | /opt/nodejs |

---

## 🔧 FFmpeg打包方案对比

### 方案1: 自己打包FFmpeg到依赖层 ⭐ 可行但复杂

#### 优势
- ✅ 无API调用费用
- ✅ 离线可用
- ✅ 完全控制

#### 劣势
- ❌ FFmpeg体积大（50-100MB）
- ❌ 需要特定平台编译
- ❌ 冷启动较慢
- ❌ 维护成本高

#### 实施步骤

**Step 1: 获取FunctionGraph运行环境信息**

华为云FunctionGraph Python运行时基于：
- 操作系统：CentOS 7.6 / Ubuntu 18.04
- 架构：x86_64
- Python：3.9 / 3.11

**Step 2: 下载或编译FFmpeg**

选项A：下载静态编译版本（推荐）
```bash
# 下载适用于Linux x86_64的静态FFmpeg
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

# 解压
tar xf ffmpeg-release-amd64-static.tar.xz
cd ffmpeg-*-amd64-static/

# 检查大小
ls -lh ffmpeg ffprobe
# ffmpeg: ~100MB (包含所有codec)
# ffprobe: ~100MB
```

选项B：自己编译（最小化体积）
```bash
# 在CentOS 7或Ubuntu 18.04环境中编译
./configure --disable-doc --disable-x86asm --enable-static
make
strip ffmpeg  # 去除调试符号，减小体积
```

**Step 3: 创建依赖层目录结构**

华为云要求的目录结构：
```
layer/
└── python/           # 固定目录名
    ├── bin/
    │   ├── ffmpeg    # 主程序
    │   └── ffprobe   # 探测工具
    └── lib/          # 如果有动态链接库
        └── ...
```

**注意事项：**
- 必须是`python/`目录（不是`opt/python/`）
- 华为云会自动挂载到`/opt/python/`

**Step 4: 压缩并上传**

```bash
cd layer
zip -r ffmpeg-layer.zip python/

# 检查大小（必须<100MB）
ls -lh ffmpeg-layer.zip
```

上传到华为云：
1. 控制台 → FunctionGraph → 依赖包管理 → 创建依赖包
2. 选择文件：ffmpeg-layer.zip
3. 运行时：Python 3.11
4. 创建

**Step 5: 函数中使用**

```python
import os
import subprocess

# FFmpeg路径
FFMPEG_PATH = '/opt/python/bin/ffmpeg'

def handler(event, context):
    # 检查FFmpeg是否存在
    if not os.path.exists(FFMPEG_PATH):
        return {'error': 'FFmpeg not found'}

    # 使用FFmpeg
    cmd = [FFMPEG_PATH, '-version']
    result = subprocess.run(cmd, capture_output=True, text=True)

    return {'output': result.stdout}
```

**Step 6: 关联依赖层到函数**

1. 进入你的函数配置
2. 添加层 → 选择刚创建的ffmpeg层
3. 保存配置

---

### 方案2: 使用华为云MPC ⭐⭐⭐ 强烈推荐

#### 为什么推荐MPC？

| 对比项 | 打包FFmpeg | 使用MPC |
|-------|-----------|---------|
| 部署难度 | ⭐ 困难 | ⭐⭐⭐ 简单 |
| 函数包大小 | 50-100MB | <5MB |
| 冷启动时间 | 5-10秒 | <1秒 |
| 功能完整度 | ⭐⭐⭐ | ⭐⭐⭐ |
| 处理速度 | 中等 | 快（分布式） |
| 成本 | 免费但占资源 | 按量付费 |
| 维护成本 | 高 | 低 |
| 扩展性 | 受函数限制 | 自动扩展 |

#### 成本对比

**打包FFmpeg的隐性成本：**
- 函数执行时间更长（处理10分钟视频需要1-2分钟）
- 内存占用更大（需要512MB-1GB内存）
- 冷启动慢（影响用户体验）
- 函数执行费用：0.00011108元/GB秒
  - 1GB内存 × 120秒 = 0.013元/次
  - 月度100次 = 1.3元

**使用MPC的成本：**
- 视频拼接：0.0654元/分钟
- 10分钟视频 = 0.65元/次
- 月度10次 = 6.5元

**结论：**
- 小量处理（<20次/月）：MPC更划算
- 大量处理（>100次/月）：打包FFmpeg更划算
- 但考虑到开发维护成本，MPC总体更优

---

## 🎯 我的建议

### 对于你的作业项目

#### 当前阶段（本地开发+演示）

**推荐配置：**
```python
# 使用双模式架构（已实现）
# .env 配置
LOCAL_MODE=true   # 本地开发
# 使用本地FFmpeg，快速迭代

LOCAL_MODE=false  # 云端演示
# 使用华为云MPC，展示云原生
```

**理由：**
1. ✅ 本地开发快速方便
2. ✅ 云端演示专业可靠
3. ✅ 体现云原生思想
4. ✅ 无需打包FFmpeg的复杂操作
5. ✅ 成本可控（演示几次<10元）

#### 如果一定要打包FFmpeg（不推荐）

**场景：**
- 需要离线运行
- 需要特殊FFmpeg功能（MPC不支持）
- 大量处理（>1000次/月）

**步骤：**
1. 下载静态编译FFmpeg
2. 精简不需要的codec（减小体积）
3. 打包到依赖层
4. 测试并优化

**预期问题：**
- 首次部署会遇到各种坑
- 需要反复调试路径和权限
- 可能需要1-2天时间

---

## 🚀 实战：快速打包FFmpeg依赖层

如果你真的要尝试，这是最快的方法：

### 快速脚本

```bash
#!/bin/bash
# 名称：build-ffmpeg-layer.sh

# 1. 下载静态FFmpeg
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar xf ffmpeg-release-amd64-static.tar.xz

# 2. 创建层目录结构
mkdir -p layer/python/bin

# 3. 复制FFmpeg
cp ffmpeg-*-amd64-static/ffmpeg layer/python/bin/
cp ffmpeg-*-amd64-static/ffprobe layer/python/bin/

# 4. 精简（可选）
strip layer/python/bin/ffmpeg
strip layer/python/bin/ffprobe

# 5. 设置权限
chmod +x layer/python/bin/ffmpeg
chmod +x layer/python/bin/ffprobe

# 6. 打包
cd layer
zip -r ../ffmpeg-layer.zip python/

# 7. 检查大小
echo "层大小:"
ls -lh ../ffmpeg-layer.zip

# 如果>100MB，需要进一步精简
```

### 测试代码

```python
# test_ffmpeg_layer.py
import os
import subprocess

def handler(event, context):
    ffmpeg_path = '/opt/python/bin/ffmpeg'

    # 测试1: 检查文件存在
    exists = os.path.exists(ffmpeg_path)
    print(f"FFmpeg exists: {exists}")

    # 测试2: 检查权限
    executable = os.access(ffmpeg_path, os.X_OK)
    print(f"FFmpeg executable: {executable}")

    # 测试3: 运行版本命令
    try:
        result = subprocess.run(
            [ffmpeg_path, '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"FFmpeg output: {result.stdout[:200]}")
        return {'status': 'success', 'version': result.stdout[:200]}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
```

---

## 📚 延伸阅读

### 华为云FunctionGraph文档

- [依赖包管理](https://support.huaweicloud.com/usermanual-functiongraph/functiongraph_01_0319.html)
- [函数依赖层](https://support.huaweicloud.com/bestpractice-functiongraph/functiongraph_05_0100.html)

### FFmpeg资源

- [静态编译版本](https://johnvansickle.com/ffmpeg/)
- [官方文档](https://ffmpeg.org/documentation.html)

---

## 🎯 最终建议

### 对于你的作业

**✅ 推荐：使用华为云MPC**
- 简单可靠
- 云原生设计
- 成本可控
- 符合作业要求

**❌ 不推荐：打包FFmpeg**
- 复杂易出错
- 部署时间长
- 没有明显优势
- 不是云原生思路

### 如果老师问为什么不打包FFmpeg

**回答模板：**
> "我们评估了两种方案。考虑到：
> 1. 华为云MPC是云原生服务，更符合Serverless理念
> 2. MPC提供更好的性能和扩展性
> 3. 打包FFmpeg会增加函数包体积，影响冷启动
> 4. 作为企业级应用，应优先选择官方托管服务
>
> 因此我们选择了MPC方案，体现了云原生的最佳实践。"

---

**总结：**
- 华为云支持依赖层 ✅
- 可以打包FFmpeg ✅
- 但不建议这么做 ⭐
- 用MPC更好 ⭐⭐⭐
