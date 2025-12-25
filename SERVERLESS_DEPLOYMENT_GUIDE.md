# Video Vault Serverless部署完整指南

## 🎯 部署架构概览

```
用户上传视频
    │
    ▼
OBS Bucket (uploads/)
    │
    │ [触发]
    ▼
┌─────────────────────┐
│ video_slicer_func   │  切片函数 (1个)
└──────────┬──────────┘
           │
           │ [并行调用]
           ▼
┌─────────────────────┐
│ dlp_scanner_func    │  DLP扫描函数 (N个并行)
└──────────┬──────────┘
           │
           │ [完成后调用]
           ▼
┌─────────────────────┐
│ video_merger_func   │  合并函数 (1个)
└──────────┬──────────┘
           │
           ▼
OBS Bucket (outputs/)
```

**资源评估（400个函数配额）：**
- video_slicer: 1个实例
- dlp_scanner: 最多380个并行实例
- video_merger: 1个实例
- AI Agent等其他函数: 18个

**可支持规模：**
- 单个视频最多380个切片 = 380分钟视频（6小时+）
- 多个视频同时处理：理论上可同时处理数十个视频

---

## 📋 部署前准备

### 1. 华为云账号准备

✅ **已有资源：**
- 华为云账号
- 函数工作流配额：400个

⏳ **需要开通的服务：**
- [ ] OBS（对象存储）
- [ ] RDS（关系型数据库）
- [ ] FunctionGraph（函数工作流）
- [ ] OCR（文字识别）
- [ ] MPC（媒体处理）- 可选

### 2. 获取访问密钥

1. 登录华为云控制台
2. 右上角点击用户名 > **我的凭证**
3. 左侧菜单选择 **访问密钥**
4. 点击 **新增访问密钥**
5. 下载CSV文件，保存AK和SK

**安全提示：**
- ⚠️ 不要将AK/SK提交到Git
- ⚠️ 定期轮换密钥
- ⚠️ 使用IAM子账号代替主账号

### 3. 选择部署方案

参考 `DEPENDENCY_LAYER_GUIDE.md`：

- **方案A（推荐）**：使用华为云OCR + MPC服务
  - ✅ 简单快速
  - ✅ 包体积小（~35MB）
  - ✅ 冷启动快（2-3秒）

- **方案B**：使用FFmpeg + Tesseract依赖层
  - ✅ 完全自主控制
  - ⚠️ 包体积大（~190MB）
  - ⚠️ 冷启动慢（10-20秒）

**本指南以方案A为例**

---

## 🗂️ 第一步：创建OBS Bucket

### 1. 创建Bucket

```bash
# 方式1: 控制台创建
# 华为云控制台 > OBS > 创建桶

# 方式2: 命令行创建
pip install esdk-obs-python

python << EOF
from obs import ObsClient

obs_client = ObsClient(
    access_key_id='你的AK',
    secret_access_key='你的SK',
    server='https://obs.cn-north-4.myhuaweicloud.com'
)

# 创建Bucket
obs_client.createBucket('video-vault-storage')
print("Bucket创建成功")
EOF
```

### 2. 创建目录结构

在Bucket中创建以下目录：
```
video-vault-storage/
├── uploads/          # 原始视频上传目录
├── slices/          # 视频切片临时目录
├── processed/       # 处理后的切片
└── outputs/         # 最终输出视频
```

**方式1: 控制台创建**
- OBS > video-vault-storage > 新建文件夹

**方式2: 代码创建**
```python
# 目录会在首次上传时自动创建，无需手动创建
```

### 3. 配置OBS触发器准备

记录以下信息（后续配置触发器时使用）：
- Bucket名称: `video-vault-storage`
- 区域: `cn-north-4`
- 触发路径: `uploads/`

---

## 🗄️ 第二步：创建RDS数据库

### 1. 创建MySQL实例

```bash
# 控制台创建步骤：
# 华为云控制台 > RDS > 创建数据库实例

# 配置选择：
- 实例名称: video-vault-db
- 数据库引擎: MySQL 8.0
- 实例规格: 入门级（2核4GB） - 可按需调整
- 存储空间: 40GB - 可按需调整
- VPC: 默认VPC或新建
- 子网: 选择可用子网
- 安全组: 允许3306端口访问
```

### 2. 创建数据库和表

```bash
# 登录RDS实例
mysql -h <RDS实例地址> -u root -p

# 创建数据库
CREATE DATABASE video_vault DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE video_vault;

# 导入表结构
SOURCE /path/to/sql/schema.sql;

# 验证
SHOW TABLES;
```

**或者使用SQL脚本**（参考 `sql/schema.sql`）

### 3. 配置数据库连接白名单

```bash
# 控制台配置步骤：
# RDS实例详情 > 连接管理 > 安全组规则

# 添加FunctionGraph的出口IP段
# 或者使用VPC内网访问（推荐）
```

### 4. 记录数据库连接信息

更新 `.env` 文件：
```env
DB_HOST=rds-xxx.cn-north-4.rds.myhuaweicloud.com
DB_PORT=3306
DB_NAME=video_vault
DB_USER=root
DB_PASSWORD=你的数据库密码
```

---

## 📦 第三步：准备依赖层

### 方案A：Python依赖 + 项目代码

#### 1. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 2. 安装依赖

```bash
mkdir -p layers/python-deps/python
cd layers/python-deps

pip install -t python/ \
    opencv-python-headless==4.8.1.78 \
    numpy==1.24.3 \
    Pillow==10.0.0 \
    requests==2.31.0 \
    PyMySQL==1.1.0 \
    huaweicloudsdkcore==3.1.60 \
    huaweicloudsdkobs==3.23.3 \
    huaweicloudsdkocr==3.1.60 \
    huaweicloudsdkmpc==3.1.60 \
    huaweicloudsdkfunctiongraph==3.1.60
```

#### 3. 添加项目代码

```bash
# 复制shared目录
cp -r ../../shared python/

# 验证结构
ls python/
# 应该看到: cv2/ numpy/ PIL/ shared/ 等
```

#### 4. 打包

```bash
# Windows
powershell Compress-Archive -Path python/* -DestinationPath python-deps.zip

# Linux/Mac
zip -r python-deps.zip python/
```

#### 5. 检查包大小

```bash
# Windows
dir python-deps.zip

# Linux/Mac
du -h python-deps.zip
```

**预期大小：** 30-40MB

如果超过100MB，需要优化：
```bash
# 删除不必要的文件
find python/ -type d -name "tests" -exec rm -rf {} +
find python/ -type d -name "__pycache__" -exec rm -rf {} +
find python/ -name "*.pyc" -delete
```

---

## 🚀 第四步：上传依赖层

### 方法1: 控制台上传

1. 登录华为云控制台
2. **FunctionGraph** > **依赖管理** > **创建依赖**
3. 填写信息：
   ```
   依赖包名称: python-deps
   运行时: Python 3.9
   上传方式: 本地上传
   选择文件: python-deps.zip
   ```
4. 点击 **确定**
5. 等待上传完成（可能需要几分钟）

### 方法2: API上传（推荐，适合大文件）

```python
import requests
import os

# 获取上传URL
auth_url = "https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens"
auth_payload = {
    "auth": {
        "identity": {
            "methods": ["password"],
            "password": {
                "user": {
                    "domain": {"name": "你的账号名"},
                    "name": "你的用户名",
                    "password": "你的密码"
                }
            }
        },
        "scope": {
            "project": {"name": "cn-north-4"}
        }
    }
}

response = requests.post(auth_url, json=auth_payload)
token = response.headers['X-Subject-Token']

# 上传依赖层
upload_url = "https://functiongraph.cn-north-4.myhuaweicloud.com/v2/{project_id}/fgs/dependencies"
headers = {
    "X-Auth-Token": token,
    "Content-Type": "application/json"
}

with open('python-deps.zip', 'rb') as f:
    files = {'file': f}
    data = {
        'name': 'python-deps',
        'runtime': 'Python3.9',
        'description': 'Video Vault Python dependencies'
    }
    response = requests.post(upload_url, headers=headers, data=data, files=files)
    print(response.json())
```

---

## ⚙️ 第五步：创建并部署函数

### 函数1: video_slicer

#### 1. 打包函数代码

```bash
cd functions
zip video_slicer.zip video_slicer_handler.py
```

#### 2. 创建函数

**控制台创建：**
1. **FunctionGraph** > **函数列表** > **创建函数**
2. 选择 **从零开始创建**
3. 填写信息：
   ```
   函数名称: video-vault-slicer
   所属应用: 新建应用 "video-vault"
   运行时: Python 3.9
   函数类型: 事件函数
   代码上传方式: 本地上传
   选择文件: video_slicer.zip
   函数执行入口: video_slicer_handler.handler
   ```

#### 3. 配置函数

**基本设置：**
- 内存: 512MB
- 超时时间: 300秒
- 并发实例数: 100

**环境变量：**
```env
HUAWEI_CLOUD_AK=你的AK
HUAWEI_CLOUD_SK=你的SK
HUAWEI_CLOUD_REGION=cn-north-4
OBS_BUCKET_NAME=video-vault-storage
DB_HOST=rds-xxx.myhuaweicloud.com
DB_PORT=3306
DB_NAME=video_vault
DB_USER=root
DB_PASSWORD=你的数据库密码
LOCAL_MODE=false
SLICE_DURATION=60
DLP_SCANNER_FUNCTION_URN=urn:fgs:cn-north-4:xxx:function:default:video-vault-dlp:latest
```

**关联依赖层：**
- 选择依赖: `python-deps`

#### 4. 配置OBS触发器

1. 函数详情 > **触发器** > **创建触发器**
2. 选择触发器类型: **对象存储服务 OBS**
3. 配置：
   ```
   桶名称: video-vault-storage
   事件: ObjectCreated:Put
   前缀: uploads/
   后缀: .mp4
   ```
4. 点击 **确定**

---

### 函数2: dlp_scanner

#### 1. 打包并创建

```bash
cd functions
zip dlp_scanner.zip dlp_scanner_handler.py
```

按照类似步骤创建函数：
```
函数名称: video-vault-dlp
入口函数: dlp_scanner_handler.handler
内存: 1024MB
超时时间: 600秒
并发实例数: 300  # 关键：支持大规模并行
```

**环境变量：** 同上，另外添加：
```env
VIDEO_MERGER_FUNCTION_URN=urn:fgs:cn-north-4:xxx:function:default:video-vault-merger:latest
OCR_CONFIDENCE_THRESHOLD=0.6
BLUR_INTENSITY=51
```

**关联依赖层：** `python-deps`

---

### 函数3: video_merger

#### 1. 打包并创建

```bash
cd functions
zip video_merger.zip video_merger_handler.py
```

创建函数：
```
函数名称: video-vault-merger
入口函数: video_merger_handler.handler
内存: 1024MB
超时时间: 900秒  # 合并耗时较长
并发实例数: 10
```

**环境变量：** 同上

**关联依赖层：** `python-deps`

---

## 🔗 第六步：配置函数URN

获取每个函数的URN并更新环境变量：

1. **FunctionGraph** > **函数列表** > 选择函数
2. 复制函数URN（格式：`urn:fgs:region:project_id:function:package:function_name:version`）
3. 更新其他函数的环境变量：
   - video_slicer函数的 `DLP_SCANNER_FUNCTION_URN`
   - dlp_scanner函数的 `VIDEO_MERGER_FUNCTION_URN`

---

## 🧪 第七步：测试部署

### 1. 测试video_slicer

**上传测试视频：**
```bash
# 使用OBS Browser工具或API上传
# 上传到: video-vault-storage/uploads/test.mp4
```

**查看函数日志：**
1. **FunctionGraph** > **函数列表** > video-vault-slicer
2. **日志** > 查看执行日志
3. 确认：
   - ✅ 视频已下载
   - ✅ 切片完成
   - ✅ 切片已上传到OBS
   - ✅ 触发了DLP扫描函数

### 2. 测试dlp_scanner

**查看日志：**
- 应该看到多个dlp_scanner实例并行执行
- 每个实例处理一个切片
- 检测敏感信息并脱敏
- 写入审计日志到数据库

### 3. 测试video_merger

**查看日志：**
- 所有切片处理完成后自动触发
- 下载处理后的切片
- 合并视频
- 上传到outputs/

### 4. 验证结果

**检查OBS：**
```bash
# 应该看到：
video-vault-storage/
├── uploads/test.mp4        # 原始视频
├── slices/xxx/             # 切片文件
├── processed/xxx/          # 处理后的切片
└── outputs/xxx_sanitized.mp4  # 最终输出
```

**检查数据库：**
```sql
-- 查看视频记录
SELECT * FROM videos;

-- 查看审计日志
SELECT * FROM audit_logs;
```

---

## 📊 第八步：监控和优化

### 1. 配置监控告警

**FunctionGraph控制台：**
1. **监控** > **创建告警规则**
2. 配置指标：
   - 函数执行错误率 > 5%
   - 函数执行超时 > 3次/分钟
   - 并发实例数 > 350

### 2. 性能优化

**调整并发配额：**
```
video_slicer: 10 实例
dlp_scanner: 350 实例  # 主要并发
video_merger: 10 实例
其他函数: 30 实例
```

**内存优化：**
- 根据实际运行情况调整
- 查看函数指标 > 内存使用率
- 适当提高内存可减少执行时间

### 3. 成本优化

**使用预留实例：**
- 对于高频函数（dlp_scanner）
- 可购买预留实例降低成本

**配置生命周期规则：**
```
OBS Bucket > 生命周期管理
- slices/: 保留1天
- processed/: 保留3天
- outputs/: 长期保留
```

---

## 🎯 完成检查清单

- [ ] OBS Bucket已创建并配置
- [ ] RDS数据库已创建并导入表结构
- [ ] 依赖层已打包并上传
- [ ] 3个函数已创建并配置
- [ ] OBS触发器已配置
- [ ] 函数URN已相互关联
- [ ] 测试视频处理流程成功
- [ ] 监控告警已配置
- [ ] 文档已归档

---

## 🆘 故障排查

### 问题1: 函数执行超时

**原因：**
- 视频太大
- 内存不足
- 网络慢

**解决：**
```
1. 增加超时时间（最大900秒）
2. 提高内存配置
3. 减小切片时长（SLICE_DURATION）
```

### 问题2: 依赖层加载失败

**错误：** `ModuleNotFoundError: No module named 'xxx'`

**解决：**
```
1. 检查依赖层路径: sys.path.insert(0, '/opt/python')
2. 验证依赖层包含该模块
3. 重新打包依赖层
```

### 问题3: OBS访问权限错误

**错误：** `AccessDenied`

**解决：**
```
1. 检查AK/SK是否正确
2. 检查IAM权限（OBS FullAccess）
3. 检查Bucket策略
```

### 问题4: 数据库连接失败

**错误：** `Can't connect to MySQL server`

**解决：**
```
1. 检查安全组规则
2. 使用VPC内网访问
3. 验证数据库连接信息
```

---

## 📚 相关文档

- `DEPENDENCY_LAYER_GUIDE.md` - 依赖层详细打包指南
- `HUAWEI_CLOUD_SETUP.md` - 华为云服务配置
- `CLOUD_NATIVE_ARCHITECTURE.md` - 云原生架构说明
- `AI_ASSISTANT_SETUP.md` - AI助手配置

---

**部署完成！** 🎉

你的Video Vault现在已经运行在华为云Serverless架构上了！
