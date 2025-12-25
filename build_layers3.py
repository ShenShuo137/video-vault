#!/usr/bin/env python3
"""
Video Vault 依赖层打包脚本
快速打包Python依赖层和函数代码（不指定版本，安装最新稳定版）
"""
import os
import sys
import subprocess
import shutil
import zipfile


def print_step(msg):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def create_python_deps_layer():
    """创建Python依赖层（不指定版本）"""
    print_step("1. 创建Python依赖层")

    # 先清理旧的依赖层目录，避免残留文件导致冲突
    layer_root = "layers/python-deps"
    if os.path.exists(layer_root):
        print("清理旧的依赖层目录...")
        shutil.rmtree(layer_root)
    
    # 创建目录（符合华为云函数层规范）
    layer_dir = "layers/python-deps/python"
    os.makedirs(layer_dir, exist_ok=True)

    # 安装依赖（完全对齐requirements.txt，不指定版本）
    print("安装Python依赖（最新稳定版）...")
    packages = [
        # 华为云 SDK（对齐requirements.txt）
        "huaweicloudsdkcore",
        "huaweicloudsdkobs",
        "huaweicloudsdkocr",
        "huaweicloudsdkfunctiongraph",
        "huaweicloudsdkmpc",
        "esdk-obs-python",  # OBS SDK 补充（保持兼容）

        # 视频处理（对齐requirements.txt）
        "opencv-python",    # 替换原headless版，和requirements.txt一致
        "ffmpeg-python",
        "Pillow",
        "numpy",

        # OCR（对齐requirements.txt）
        "pytesseract",

        # 数据库（对齐requirements.txt）
        "PyMySQL",

        # Web框架（对齐requirements.txt）
        "Flask",
        "Flask-CORS",
        "requests",

        # 工具（对齐requirements.txt）
        "python-dotenv",
        "colorlog",
        "tqdm",
        "jinja2",
        "python-dateutil",
        "typing-extensions",
        "cryptography",

        # AI Agent（对齐requirements.txt）
        "openai"
    ]

    # 批量构建pip命令（统一配置，避免重复）
    # ⚠️ 重要：必须使用Python 3.9打包（与华为云运行时一致）
    # Windows用户：如果安装了Python 3.9，请将下面的 sys.executable 改为 "py -3.9"
    # Linux/Mac用户：改为 "python3.9"
    python_executable = sys.executable  # 默认使用当前Python

    # 检查Python版本
    import platform
    py_version = platform.python_version()
    if not py_version.startswith('3.9'):
        print(f"\n⚠️  警告: 当前Python版本为 {py_version}")
        print("   华为云FunctionGraph使用Python 3.9运行时")
        print("   建议使用Python 3.9打包以避免兼容性问题")
        print("\n   解决方案:")
        print("   1. 安装Python 3.9: https://www.python.org/downloads/release/python-3913/")
        print("   2. Windows: 修改本文件第78行为 'py -3.9'")
        print("   3. Linux/Mac: 修改本文件第78行为 'python3.9'")
        response = input("\n是否继续使用当前Python版本打包? (y/N): ")
        if response.lower() != 'y':
            print("已取消打包")
            return False

    base_cmd = [
        python_executable, "-m", "pip", "install", 
        "-t", layer_dir,                      # 安装到指定目录
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",  # 清华镜像加速
        "--upgrade",                          # 强制升级/覆盖
        "--no-cache-dir"                      # 不缓存，减小体积
    ]

    # 拆分安装：先装普通包，再装华为云SDK（避免--no-deps影响其他包）
    huawei_pkgs = [p for p in packages if "huaweicloud" in p or "esdk-obs" in p]
    normal_pkgs = [p for p in packages if p not in huawei_pkgs]

    # 安装普通包（不使用--no-deps）
    if normal_pkgs:
        print("\n安装普通依赖包...")
        cmd = base_cmd + normal_pkgs
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 普通包安装失败: {e}")
            return False

    # 安装华为云SDK（使用--no-deps避免冲突）
    if huawei_pkgs:
        print("\n安装华为云SDK（禁用依赖检查）...")
        cmd = base_cmd + ["--no-deps"] + huawei_pkgs
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 华为云SDK安装失败: {e}")
            return False

    # 复制项目代码（容错处理）
    print("\n复制项目代码...")
    if os.path.exists("shared"):
        shutil.copytree("shared", os.path.join(layer_dir, "shared"), dirs_exist_ok=True)
    else:
        print("⚠️  警告: shared目录不存在，跳过复制")

    # 清理冗余文件（减小包体积）
    print("清理不必要的文件...")
    for root, dirs, files in os.walk(layer_dir):
        # 删除测试/缓存目录
        for dir_name in ['tests', '__pycache__', '.dist-info', '.egg-info']:
            if dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                shutil.rmtree(dir_path, ignore_errors=True)
                dirs.remove(dir_name)  # 避免重复遍历

        # 删除.pyc/.pyo等编译文件
        for file in files:
            if file.endswith(('.pyc', '.pyo', '.pyd', '.so')) and 'site-packages' not in root:
                try:
                    os.remove(os.path.join(root, file))
                except Exception:
                    pass

    # 打包依赖层
    print("\n打包依赖层...")
    zip_path = "layers/python-deps.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(layer_dir))
                zipf.write(file_path, arcname)

    # 检查包体积（华为云函数层限制100MB）
    size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n✅ 依赖层打包完成: {zip_path}")
    print(f"   大小: {size:.2f} MB")

    if size > 100:
        print(f"⚠️  警告: 文件大小超过100MB限制! 建议清理部分依赖或指定版本")
        return False

    return True


def create_function_packages():
    """打包函数代码"""
    print_step("2. 打包函数代码")

    functions = [
        ("video_slicer_handler.py", "video_slicer.zip"),
        ("dlp_scanner_handler.py", "dlp_scanner.zip"),
        ("video_merger_handler.py", "video_merger.zip"),
        ("ai_agent_handler.py", "ai_agent.zip")
    ]

    os.makedirs("deploy", exist_ok=True)

    for handler, zip_name in functions:
        handler_path = os.path.join("functions", handler)

        if not os.path.exists(handler_path):
            print(f"⚠️  跳过: {handler} 不存在")
            continue

        zip_path = os.path.join("deploy", zip_name)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 打包handler文件
            zipf.write(handler_path, os.path.basename(handler_path))

            # 特殊处理：ai_agent需要打包整个ai_agent目录
            if handler == "ai_agent_handler.py":
                ai_agent_dir = os.path.join("functions", "ai_agent")
                if os.path.exists(ai_agent_dir):
                    # 打包ai_agent目录下的所有Python文件
                    for root, dirs, files in os.walk(ai_agent_dir):
                        for file in files:
                            if file.endswith('.py') and file not in ['__init__.py', 'agent.py', 'tools.py']:
                                # 跳过旧版文件（agent.py, tools.py），只打包Serverless版本
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, "functions")
                                zipf.write(file_path, f"functions/{arcname}")
                                print(f"   + {arcname}")

        size = os.path.getsize(zip_path) / 1024
        print(f"✅ {zip_name}: {size:.2f} KB")

    return True


def verify_env_config():
    """验证环境配置（逻辑不变，增强容错）"""
    print_step("3. 验证环境配置")

    required_vars = [
        "HUAWEI_CLOUD_AK",
        "HUAWEI_CLOUD_SK",
        "OBS_BUCKET_NAME",
        "DB_HOST",
        "DB_PASSWORD"
    ]

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  警告: python-dotenv未安装，跳过环境变量验证")
        return True

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_') or value == '':
            missing.append(var)
            print(f"❌ {var}: 未配置")
        else:
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
            print(f"✅ {var}: {masked}")

    if missing:
        print(f"\n⚠️  缺少配置: {', '.join(missing)}")
        print("   请在 .env 文件中配置这些变量")
        return False

    return True


def print_deployment_summary():
    """打印部署摘要（逻辑不变）"""
    print_step("部署文件已准备好")

    print("📦 依赖层:")
    print("   layers/python-deps.zip")

    print("\n📄 函数代码:")
    if os.path.exists("deploy"):
        for file in os.listdir("deploy"):
            if file.endswith('.zip'):
                size = os.path.getsize(os.path.join("deploy", file)) / 1024
                print(f"   deploy/{file} ({size:.2f} KB)")

    print("\n📚 下一步:")
    print("   1. 登录华为云控制台")
    print("   2. 上传依赖层: layers/python-deps.zip")
    print("   3. 创建4个函数并上传代码:")
    print("      - video-vault-slicer (deploy/video_slicer.zip)")
    print("      - video-vault-dlp (deploy/dlp_scanner.zip)")
    print("      - video-vault-merger (deploy/video_merger.zip)")
    print("      - video-vault-ai-agent (deploy/ai_agent.zip)")
    print("   4. 配置环境变量和触发器")
    print("   5. 测试部署")
    print("\n详细步骤请参考: FUNCTIONGRAPH_DEPLOYMENT_GUIDE.md")


def main():
    """主函数（逻辑不变）"""
    print("""
╔══════════════════════════════════════════════════════════╗
║          Video Vault 依赖层打包工具                      ║
║          Dependency Layer Packaging Tool                  ║
╚══════════════════════════════════════════════════════════╝
    """)

    try:
        if not create_python_deps_layer():
            print("\n❌ 依赖层打包失败")
            return 1

        if not create_function_packages():
            print("\n❌ 函数代码打包失败")
            return 1

        verify_env_config()
        print_deployment_summary()

        print("\n✅ 打包完成!")
        return 0

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())