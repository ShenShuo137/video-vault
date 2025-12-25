# OBS 桶目录结构说明

## ⚠️ 重要提示

**OBS 不需要预先手动创建目录！**

华为云 OBS 是对象存储，目录（前缀）会在上传文件时自动创建。你只需要：
1. 创建 OBS 桶：`video-vault-storage`
2. 配置 CORS（如果前端直接访问）
3. 代码会自动创建所需的"目录"结构

## 完整目录结构

```
video-vault-storage/
│
├── uploads/                              # 前端上传的原始视频
│   └── <video_id>.mp4                   # 例如：1735123456789-meeting.mp4
│                                         # ⚡ OBS触发器监听此目录，触发 video-vault-slicer 函数
│
├── slices/                              # 视频切片（由 slicer 生成）
│   └── <video_id>/
│       ├── slice_0000.mp4              # 第1个切片
│       ├── slice_0001.mp4              # 第2个切片
│       └── ...                          # 更多切片
│
├── processed/                           # DLP处理后的切片（由 dlp-scanner 生成）
│   └── <video_id>/
│       ├── slice_0000.mp4              # 处理后的第1个切片
│       ├── slice_0001.mp4              # 处理后的第2个切片
│       └── ...                          # 更多处理后的切片
│
├── logs/                                # 审计日志（由 dlp-scanner 生成）
│   └── <video_id>_audit.json           # 例如：1735123456789-meeting_audit.json
│                                        # 前端会读取此文件获取敏感信息检测结果
│
└── outputs/                             # 最终输出视频（由 merger 生成）
    └── <video_id>_sanitized.mp4        # 例如：1735123456789-meeting_sanitized.mp4
                                         # 前端会列出此目录下的所有视频

```

## 处理流程与目录关系

### 1️⃣ 视频上传阶段
```
前端 → uploads/<video_id>.mp4
       ↓ (OBS触发器)
     video-vault-slicer 函数启动
```

### 2️⃣ 视频切片阶段
```
video-vault-slicer 函数:
  读取: uploads/<video_id>.mp4
  写入: slices/<video_id>/slice_0000.mp4
       slices/<video_id>/slice_0001.mp4
       ...
  调用: video-vault-dlp-scanner 函数 (并行调用多次)
```

### 3️⃣ DLP扫描阶段
```
video-vault-dlp-scanner 函数 (每个切片):
  读取: slices/<video_id>/slice_XXXX.mp4
  写入: processed/<video_id>/slice_XXXX.mp4  (脱敏后)
       logs/<video_id>_audit.json           (追加检测结果)

最后一个切片处理完成后:
  调用: video-vault-merger 函数
```

### 4️⃣ 视频合并阶段
```
video-vault-merger 函数:
  读取: processed/<video_id>/slice_0000.mp4
       processed/<video_id>/slice_0001.mp4
       ...
  写入: outputs/<video_id>_sanitized.mp4
```

### 5️⃣ 前端查询阶段
```
前端查询处理状态:
  检查: outputs/<video_id>_sanitized.mp4 (是否存在)
  检查: slices/<video_id>/ (切片数量)
  检查: logs/<video_id>_audit.json (是否生成)

前端列出所有视频:
  列出: outputs/ 目录下所有 *_sanitized.mp4

前端查看审计日志:
  读取: logs/<video_id>_audit.json
```

## 审计日志文件格式

`logs/<video_id>_audit.json` 内容示例：

```json
{
  "video_id": "1735123456789-meeting",
  "total_detections": 15,
  "detections": [
    {
      "slice_index": 0,
      "frame_id": 5,
      "timestamp": 5.2,
      "type": "id_card",
      "text": "123456789012345678",
      "confidence": 0.95,
      "bbox": {
        "x": 100,
        "y": 200,
        "width": 300,
        "height": 150
      }
    },
    {
      "slice_index": 1,
      "frame_id": 3,
      "timestamp": 13.8,
      "type": "phone",
      "text": "13812345678",
      "confidence": 0.92,
      "bbox": {
        "x": 50,
        "y": 100,
        "width": 200,
        "height": 80
      }
    }
  ]
}
```

## 需要配置的 OBS 触发器

**只需要1个触发器：**

| 函数名称 | 触发器类型 | 桶名 | 前缀 | 后缀 | 事件类型 |
|---------|-----------|-----|------|------|---------|
| video-vault-slicer | OBS | video-vault-storage | `uploads/` | `.mp4` | `ObjectCreated:*` |

**其他函数不需要触发器**，它们通过函数间调用触发。

## 前端环境变量配置

```bash
VITE_OBS_BUCKET_NAME=video-vault-storage
VITE_OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com
```

## CORS 配置（前端直接访问OBS必需）

在华为云 OBS 控制台配置 CORS：

```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag", "x-obs-request-id"],
    "MaxAgeSeconds": 3600
  }
]
```

## 常见问题

### Q1: 是否需要手动创建这些目录？
**不需要！** OBS 是对象存储，不是文件系统。当你上传文件时，"目录"（前缀）会自动创建。

### Q2: 上传视频后一直卡在"等待云函数启动"？
检查以下几点：
1. **OBS 触发器是否正确配置**（最常见原因）
   - 进入 `video-vault-slicer` 函数
   - 检查 **触发器** 标签页
   - 确认有 OBS 触发器，前缀为 `uploads/`

2. **环境变量是否配置正确**
   - 所有函数都需要配置 AK/SK 等环境变量

3. **查看函数执行日志**
   - 进入函数 → **监控** → **日志**
   - 查看是否有报错

### Q3: 如何手动查看 OBS 中的文件？
使用 obsutil 命令行工具：

```bash
# 列出所有目录
obsutil ls obs://video-vault-storage/

# 查看 uploads 目录
obsutil ls obs://video-vault-storage/uploads/

# 查看某个视频的切片
obsutil ls obs://video-vault-storage/slices/1735123456789-meeting/

# 下载审计日志查看
obsutil cp obs://video-vault-storage/logs/1735123456789-meeting_audit.json ./
cat 1735123456789-meeting_audit.json
```

### Q4: 切片文件什么时候会被删除？
**不会自动删除！**

为节省存储空间，你可以：
1. 在 merger 函数完成后添加清理逻辑（删除 slices/ 和 processed/）
2. 配置 OBS 生命周期规则，自动删除 N 天前的临时文件
3. 手动定期清理

### Q5: 前端显示的处理阶段如何判断？
根据 OBS 中文件的存在情况：

| 阶段 | outputs/ | slices/ | logs/ | 前端显示 |
|-----|---------|---------|-------|---------|
| 刚上传 | ❌ | ❌ | ❌ | "等待云函数启动..." |
| 切片中 | ❌ | ❌ | ❌ | "等待云函数启动..." |
| 扫描中 | ❌ | ✅ | ❌ | "DLP扫描中 (已生成 X 个切片)" |
| 合并中 | ❌ | ✅ | ✅ | "正在合并视频..." |
| 完成 | ✅ | ✅ | ✅ | "处理完成!" |

## 调试技巧

### 1. 检查文件是否生成
```bash
# 上传后立即检查
obsutil ls obs://video-vault-storage/uploads/

# 等待30秒后检查切片
obsutil ls obs://video-vault-storage/slices/

# 等待1分钟后检查处理结果
obsutil ls obs://video-vault-storage/processed/

# 检查最终输出
obsutil ls obs://video-vault-storage/outputs/
```

### 2. 查看云函数日志
1. 进入 FunctionGraph 控制台
2. 选择函数（如 video-vault-slicer）
3. 点击 **监控** → **日志**
4. 按时间顺序查看执行日志

### 3. 前端浏览器控制台
按 F12 打开开发者工具，查看详细日志：
- 上传进度
- 状态查询结果
- 文件检查情况

## 总结

✅ **不需要手动创建目录**
✅ **只需配置1个OBS触发器**
✅ **前端会自动检查各阶段文件**
✅ **所有路径都已在代码中硬编码**

如果上传后没有反应，优先检查：
1. OBS 触发器是否配置
2. 云函数环境变量是否完整
3. 云函数执行日志中的报错
