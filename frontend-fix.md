# 前端启动错误解决方案

## 问题分析

1. Node.js 版本: 20.18.0 (需要 20.19+ 或 22.12+)
2. npm 依赖安装问题: rolldown native binding 缺失

## 解决方案

### 方案1: 清理重装依赖（先试这个）

```bash
cd frontend

# 删除依赖
rd /s /q node_modules
del package-lock.json

# 重新安装
npm install
npm run dev
```

### 方案2: 如果方案1不行，升级Node.js

下载并安装最新的 Node.js LTS 版本：
https://nodejs.org/

推荐版本: Node.js 22.x LTS

### 方案3: 使用较旧版本的Vite（不推荐但可用）

如果暂时不想升级Node.js，可以降级Vite版本：

```bash
cd frontend

# 修改 package.json 中的 vite 版本
npm install vite@5.4.11 --save-dev

npm run dev
```

## 推荐的完整修复步骤

```bash
# 1. 进入前端目录
cd D:\video-vault\frontend

# 2. 清理旧依赖
rd /s /q node_modules
del package-lock.json

# 3. 使用稳定版本的依赖
npm install vite@5.4.11 --save-dev

# 4. 重新安装其他依赖
npm install

# 5. 启动开发服务器
npm run dev
```
