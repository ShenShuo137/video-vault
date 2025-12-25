# 华为云部署快速指南

> 简化版部署步骤，专注核心配置

---

## 📦 需要上传的文件清单

打包完成后，你会得到这些文件：

```
video-vault/
├── layers/
│   └── python-deps.zip          ⬅️ 上传这个（依赖层，~35MB）
└── deploy/
    ├── video_slicer.zip         ⬅️ 上传这个（函数1）
    ├── dlp_scanner.zip          ⬅️ 上传这个（函数2）
    └── video_merger.zip         ⬅️ 上传这个（函数3）
```

**总共4个zip文件**

---

## 🚀 部署步骤（简化版）

### 第1步：上传依赖层（1次）

1. 登录华为云控制台
2. 进入 **FunctionGraph** 服务
3. 左侧菜单 → **函数** → **依赖包**
4. 点击 **创建依赖包**
   - **名称**: `video-vault-deps`
   - **运行时**: `Python 3.9`
   - **上传方式**: 本地ZIP包
   - **选择文件**: `layers/python-deps.zip`
5. 点击 **确定**，等待上传完成（~2分钟）

---

### 第2步：创建3个函数

#### 函数1: Video Slicer（视频切片）

1. FunctionGraph → **函数** → **创建函数**
2. 基本信息：
   - **函数名称**: `video-vault-slicer`
   - **运行时**: `Python 3.9`
   - **函数类型**: `事件函数`
3. 上传代码：
   - **上传方式**: 本地ZIP包
   - **选择文件**: `deploy/video_slicer.zip`
   - **函数执行入口**: `video_slicer_handler.handler`
4. **关联依赖层**:
   - 点击 **添加公共依赖包**
   - 选择 `video-vault-deps`（刚才创建的）
5. 配置：
   - **内存**: `512 MB`
   - **执行超时时间**: `300秒`
   - **环境变量**（点击"编辑"）:
     ```
     HUAWEI_CLOUD_AK = <你的AK>
     HUAWEI_CLOUD_SK = <你的SK>
     HUAWEI_CLOUD_REGION = cn-north-4
     OBS_BUCKET_NAME = video-vault-storage
     OBS_ENDPOINT = obs.cn-north-4.myhuaweicloud.com
     SLICE_DURATION = 30
     LOCAL_MODE = false
     DLP_SCANNER_FUNCTION_URN = （暂时留空，后面填）
     ```
6. 点击 **创建函数**

#### 函数2: DLP Scanner（DLP扫描）

重复上述步骤，但：
- **函数名称**: `video-vault-dlp`
- **代码包**: `deploy/dlp_scanner.zip`
- **函数执行入口**: `dlp_scanner_handler.handler`
- **内存**: `1024 MB`（需要更多内存用于OCR）
- **环境变量**: 同上，但添加：
  ```
  OCR_CONFIDENCE_THRESHOLD = 0.8
  BLUR_INTENSITY = 25
  VIDEO_MERGER_FUNCTION_URN = （暂时留空，后面填）
  ```

#### 函数3: Video Merger（视频合并）

重复上述步骤，但：
- **函数名称**: `video-vault-merger`
- **代码包**: `deploy/video_merger.zip`
- **函数执行入口**: `video_merger_handler.handler`
- **内存**: `1024 MB`
- **环境变量**: 同函数1

---

### 第3步：配置函数URN

函数创建后，获取URN并配置相互调用：

1. 进入 **video-vault-slicer** 函数详情页
2. 复制 **函数URN**（类似：`urn:fgs:cn-north-4:xxx:function:default:video-vault-dlp`）
3. 进入 **video-vault-slicer** 的 **配置** → **环境变量**
4. 编辑 `DLP_SCANNER_FUNCTION_URN`，粘贴刚才复制的URN
5. 同样，复制 **video-vault-merger** 的URN
6. 配置到 **video-vault-dlp** 的 `VIDEO_MERGER_FUNCTION_URN`
7. 保存

---

### 第4步：配置OBS触发器

让OBS上传事件自动触发 video-slicer 函数：

1. 进入 **video-vault-slicer** 函数详情页
2. 点击 **触发器** 标签
3. 点击 **创建触发器**
4. 配置：
   - **触发器类型**: `OBS（对象存储）`
   - **桶名称**: `video-vault-storage`
   - **前缀**: `uploads/`（只监听uploads目录）
   - **后缀**: `.mp4`（只监听mp4文件）
   - **事件**: `ObjectCreated:*`（上传事件）
5. 点击 **确定**

---

### 第5步：测试部署

1. 登录OBS控制台
2. 进入 `video-vault-storage` 存储桶
3. 上传一个测试视频到 `uploads/` 目录
4. 等待几秒钟
5. 查看 FunctionGraph 函数日志：
   - video-vault-slicer 日志：应该看到切片完成
   - video-vault-dlp 日志：应该看到DLP扫描
   - video-vault-merger 日志：应该看到合并完成
6. 检查 OBS `outputs/` 目录：应该有处理后的视频

---

## 🤔 关于VPC（Virtual Private Cloud）

### VPC是什么？

**VPC = 虚拟私有云**，类似你自己的私有网络环境。

```
互联网 🌐
    ↓
VPC（你的私有网络）
    ├── 子网1: 192.168.1.0/24
    │   ├── 云服务器
    │   └── 数据库（RDS）
    └── 子网2: 192.168.2.0/24
        └── 函数工作流
```

### 我们需要配置VPC吗？

**取决于你的需求：**

#### ❌ 不需要VPC的情况（当前可用）

如果你：
- ✅ 只使用OBS、OCR、MPC等公共云服务
- ✅ 不需要数据库（或使用公网访问RDS）
- ✅ 函数间调用通过FunctionGraph API

**无需配置VPC**，保持默认即可！

#### ✅ 需要VPC的情况

如果你：
- 🔒 需要访问私有网络中的RDS数据库（更安全）
- 🔒 需要访问VPC内的其他服务（如Redis）
- 🔒 需要固定出口IP地址

**需要配置VPC和安全组**。

---

## 🎯 推荐配置

### 方案A：简单模式（推荐初学者）⭐

**不配置VPC**，所有通信走公网：

- ✅ 配置简单
- ✅ 部署快速
- ✅ 成本低
- ⚠️ 数据库需要允许公网访问（配置白名单）

**如何配置**：
- 函数创建时，VPC选择 **无**
- RDS数据库绑定弹性公网IP
- 在.env中配置RDS的公网地址

### 方案B：安全模式（推荐生产环境）

**配置VPC**，函数和数据库在同一内网：

- 🔒 更安全（数据库不暴露公网）
- 🔒 网络隔离
- ⚠️ 配置复杂
- ⚠️ 需要NAT网关（额外成本）

**如何配置**：
1. 创建VPC和子网
2. 创建RDS时选择VPC
3. 函数配置时选择同一VPC
4. 配置安全组规则
5. 配置NAT网关（函数访问外网需要）

---

## 📝 当前部署建议

**第一次部署，建议使用方案A（不配置VPC）：**

```
✅ 步骤1-4：按上述步骤部署，VPC选择"无"
✅ 步骤5：测试功能是否正常
✅ 如果需要数据库：
   - 先测试基本功能（不连数据库）
   - 确认函数正常后再配置RDS
   - RDS配置公网访问 + IP白名单
```

---

## 🚨 常见问题

### Q1: 上传依赖层太慢？
**A**: 依赖层35MB，上传需要5-10分钟，耐心等待。

### Q2: 函数调用失败404？
**A**: 检查环境变量中的 `DLP_SCANNER_FUNCTION_URN` 和 `VIDEO_MERGER_FUNCTION_URN` 是否正确配置。

### Q3: OCR识别失败？
**A**: 确认环境变量中的 `HUAWEI_CLOUD_AK`、`HUAWEI_CLOUD_SK` 正确。

### Q4: OBS操作失败？
**A**:
- 确认 `OBS_BUCKET_NAME` 存在
- 确认 `OBS_ENDPOINT` 与bucket的region一致
- 确认AK/SK有OBS权限

### Q5: 需要配置数据库吗？
**A**:
- **核心功能不需要**：视频处理、DLP扫描可以正常工作
- **可选功能需要**：审计日志存储、Web仪表盘需要数据库

---

## 📊 部署检查清单

部署前确认：
- [ ] `build_layers.py` 执行成功
- [ ] 生成了4个zip文件
- [ ] OBS bucket已创建
- [ ] OCR/MPC服务已开通
- [ ] AK/SK已准备好

部署后确认：
- [ ] 依赖层上传成功
- [ ] 3个函数创建成功
- [ ] 环境变量配置正确
- [ ] 函数URN配置完成
- [ ] OBS触发器配置成功
- [ ] 测试视频处理成功

---

## 🎉 完成！

如果所有步骤都完成，你的Serverless DLP系统就部署好了！

上传视频到 `obs://video-vault-storage/uploads/`，系统会自动：
1. 切片
2. 扫描敏感信息
3. 脱敏处理
4. 合并输出到 `outputs/`

有问题随时问我！🚀
