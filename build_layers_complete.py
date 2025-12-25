#!/usr/bin/env python3
"""
Video Vault 依赖层打包脚本 - 完整版
包含所有直接依赖和传递依赖
"""
import os
import sys
import subprocess
import shutil
import zipfile
import platform


def print_step(msg):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def create_python_deps_layer():
    """创建Python依赖层 - 完整依赖版本"""
    print_step("1. 创建Python依赖层（包含所有传递依赖）")

    # 升级 pip
    print("升级 pip 到最新版本...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                      check=True, capture_output=True)
        print("✅ pip 已升级到最新版本")
    except subprocess.CalledProcessError:
        print("⚠️ pip 升级失败，继续使用当前版本")

    # 检测环境 + 安装编译依赖（Linux）
    is_linux = platform.system() == "Linux"
    if is_linux:
        print("检测到 Linux 环境，安装编译依赖...")
        try:
            subprocess.run(["apt-get", "update"], check=True, capture_output=True)
            subprocess.run(["apt-get", "install", "-y", "gcc", "python3.9-dev"],
                          check=True, capture_output=True)
            print("✅ 编译依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ 编译依赖安装失败: {e}，继续安装...")

    # 清理旧的依赖层目录
    layer_root = "layers/python-deps"
    if os.path.exists(layer_root):
        print("清理旧的依赖层目录...")
        shutil.rmtree(layer_root)

    # 创建目录（符合华为云函数层规范）
    layer_dir = "layers/python-deps/python"
    os.makedirs(layer_dir, exist_ok=True)

    # ========== 完整依赖列表（包含所有传递依赖） ==========
    print("准备安装依赖包...")

    # 基础依赖（必须先装，其他包依赖它们）
    base_deps = [
        "six",                    # 很多包的基础依赖
        "pytz",                   # 时区处理
        "certifi",                # HTTPS 证书
        "charset-normalizer",     # requests 依赖
        "idna",                   # requests 依赖
        "urllib3",                # requests 依赖
    ]

    # 加密相关（esdk-obs-python 需要）
    crypto_deps = [
        "pycryptodome",           # ⚠️ 关键：esdk-obs-python 的 Crypto 模块
        "cryptography",           # 通用加密库
    ]

    # 华为云 SDK 及其依赖
    huawei_deps = [
        "huaweicloudsdkcore",
        "huaweicloudsdkobs",
        "huaweicloudsdkocr",
        "huaweicloudsdkfunctiongraph",
        "huaweicloudsdkmpc",
    ]

    # 需要源码安装的包（没有预编译 wheel）
    source_only_deps = [
        "crcmod",                 # 没有 manylinux wheel，需要编译
        "esdk-obs-python",        # 依赖 crcmod
    ]

    # OpenAI SDK 及其依赖
    ai_deps = [
        "httpx",                  # ⚠️ openai 的 HTTP 客户端
        "h11",                    # httpx 依赖
        "httpcore",               # httpx 依赖
        "sniffio",                # httpx 依赖
        "anyio",                  # httpx 异步支持
        "pydantic",               # ⚠️ openai 的数据验证
        "pydantic-core",          # pydantic 核心
        "annotated-types",        # pydantic 类型注解
        "typing-extensions",      # 类型扩展
        "openai",                 # OpenAI SDK
    ]

    # 视频处理依赖
    video_deps = [
        "numpy<2.0",              # 兼容 Python 3.9
        "opencv-python-headless==4.8.1.78",
        "Pillow==10.0.0",
    ]

    # OCR 依赖
    ocr_deps = [
        "pytesseract",
    ]

    # 数据库依赖
    db_deps = [
        "PyMySQL",
    ]

    # Web 框架依赖
    web_deps = [
        "click",                  # Flask 依赖
        "itsdangerous",           # Flask 依赖
        "Jinja2",                 # Flask 依赖
        "MarkupSafe",             # Jinja2 依赖
        "Werkzeug",               # Flask 依赖
        "Flask",
        "Flask-CORS",
        "requests",
    ]

    # 工具依赖
    tool_deps = [
        "python-dotenv",
        "colorlog",
        "tqdm",
        "python-dateutil",
    ]

    # 合并所有依赖包（排除需要源码安装的）
    binary_packages = (
        base_deps +
        crypto_deps +
        huawei_deps +
        ai_deps +
        video_deps +
        ocr_deps +
        db_deps +
        web_deps +
        tool_deps
    )

    print(f"总共需要安装 {len(binary_packages) + len(source_only_deps)} 个包")
    print(f"  - 预编译包: {len(binary_packages)} 个")
    print(f"  - 源码编译包: {len(source_only_deps)} 个")
    print("\n预编译包列表:")
    for i, pkg in enumerate(binary_packages, 1):
        print(f"  {i}. {pkg}")
    print(f"\n源码编译包列表:")
    for i, pkg in enumerate(source_only_deps, 1):
        print(f"  {i}. {pkg}")

    # 检查Python版本
    py_version = platform.python_version()
    if not py_version.startswith('3.9'):
        print(f"\n⚠️  警告: 当前Python版本为 {py_version}")
        print("   华为云FunctionGraph使用Python 3.9运行时")
        print("   建议使用Python 3.9打包以避免兼容性问题")
        response = input("\n是否继续使用当前Python版本打包? (y/N): ")
        if response.lower() != 'y':
            print("已取消打包")
            return False

    # 根据环境选择安装策略
    if is_linux and py_version.startswith('3.9'):
        print(f"\n✅ 检测到 Linux Python 3.9 环境，使用直接安装")
        base_cmd = [
            sys.executable, "-m", "pip", "install",
            "-t", layer_dir,
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
            "--upgrade",
            "--no-cache-dir"
        ]
    else:
        print(f"\n⚠️  当前环境: {platform.system()} Python {py_version}")
        print("   使用跨平台安装")
        base_cmd = [
            sys.executable, "-m", "pip", "install",
            "-t", layer_dir,
            "--platform", "manylinux2014_x86_64",
            "--only-binary=:all:",
            "--python-version", "39",
            "--implementation", "cp",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
            "--upgrade",
            "--no-cache-dir"
        ]

    # 分批安装预编译包（避免内存溢出）
    batch_size = 10
    for i in range(0, len(binary_packages), batch_size):
        batch = binary_packages[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(binary_packages) + batch_size - 1) // batch_size

        print(f"\n{'='*60}")
        print(f"安装预编译包批次 {batch_num}/{total_batches}")
        print(f"{'='*60}")
        for pkg in batch:
            print(f"  - {pkg}")

        cmd = base_cmd + batch
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ 批次 {batch_num} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"\n⚠️ 批次 {batch_num} 安装失败，尝试使用官方 PyPI...")
            # 尝试官方源
            if is_linux and py_version.startswith('3.9'):
                cmd_official = [
                    sys.executable, "-m", "pip", "install",
                    "-t", layer_dir,
                    "--upgrade",
                    "--no-cache-dir"
                ] + batch
            else:
                cmd_official = [
                    sys.executable, "-m", "pip", "install",
                    "-t", layer_dir,
                    "--platform", "manylinux2014_x86_64",
                    "--only-binary=:all:",
                    "--python-version", "39",
                    "--implementation", "cp",
                    "--upgrade",
                    "--no-cache-dir"
                ] + batch

            try:
                subprocess.run(cmd_official, check=True)
                print(f"✅ 批次 {batch_num} 使用官方源安装成功")
            except subprocess.CalledProcessError:
                print(f"❌ 批次 {batch_num} 安装失败: {e}")
                print(f"   失败的包: {', '.join(batch)}")
                return False

    # 安装需要源码编译的包（不使用 --only-binary）
    if source_only_deps:
        print(f"\n{'='*60}")
        print("安装源码编译包（允许从源码构建）")
        print(f"{'='*60}")
        for pkg in source_only_deps:
            print(f"  - {pkg}")

        # 不使用 --only-binary 和 --platform 参数
        if is_linux and py_version.startswith('3.9'):
            cmd_source = [
                sys.executable, "-m", "pip", "install",
                "-t", layer_dir,
                "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                "--upgrade",
                "--no-cache-dir"
            ] + source_only_deps
        else:
            # Windows 环境：尝试下载源码并在目标平台编译（可能失败）
            print("\n⚠️  警告: 源码编译包在 Windows 跨平台安装中可能失败")
            print("   建议在 Linux Python 3.9 环境中打包")
            cmd_source = [
                sys.executable, "-m", "pip", "install",
                "-t", layer_dir,
                "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                "--upgrade",
                "--no-cache-dir",
                "--no-binary", ":all:"  # 强制从源码安装
            ] + source_only_deps

        try:
            subprocess.run(cmd_source, check=True)
            print(f"✅ 源码编译包安装成功")
        except subprocess.CalledProcessError as e:
            print(f"\n⚠️ 源码编译包安装失败，尝试官方 PyPI...")
            cmd_source_official = [
                sys.executable, "-m", "pip", "install",
                "-t", layer_dir,
                "--upgrade",
                "--no-cache-dir"
            ] + source_only_deps
            try:
                subprocess.run(cmd_source_official, check=True)
                print(f"✅ 源码编译包使用官方源安装成功")
            except subprocess.CalledProcessError:
                print(f"❌ 源码编译包安装失败: {e}")
                print(f"   失败的包: {', '.join(source_only_deps)}")
                print("\n💡 解决方案:")
                print("   1. 在 Linux Python 3.9 环境中打包")
                print("   2. 或使用华为云函数环境打包 (test.py)")
                return False

    # 复制项目代码
    print("\n复制项目代码...")
    if os.path.exists("shared"):
        shutil.copytree("shared", os.path.join(layer_dir, "shared"), dirs_exist_ok=True)
        print("✅ shared/ 目录已复制")
    else:
        print("⚠️  警告: shared/ 目录不存在，跳过复制")

    # 清理冗余文件（保留 .so/.pyd）
    print("\n清理不必要的文件...")
    for root, dirs, files in os.walk(layer_dir):
        # 删除测试/缓存目录
        for dir_name in ['tests', 'test', '__pycache__', '*.dist-info', '*.egg-info']:
            if dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                shutil.rmtree(dir_path, ignore_errors=True)
                try:
                    dirs.remove(dir_name)
                except ValueError:
                    pass

        # 仅删除 .pyc/.pyo，保留 .so/.pyd
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                try:
                    os.remove(os.path.join(root, file))
                except Exception:
                    pass

    # 验证关键依赖
    print("\n验证关键依赖安装...")
    critical_modules = {
        "numpy": os.path.join(layer_dir, "numpy", "__init__.py"),
        "cv2": os.path.join(layer_dir, "cv2", "__init__.py"),
        "obs": os.path.join(layer_dir, "obs", "__init__.py"),
        "Crypto": os.path.join(layer_dir, "Crypto", "__init__.py"),
        "openai": os.path.join(layer_dir, "openai", "__init__.py"),
        "httpx": os.path.join(layer_dir, "httpx", "__init__.py"),
        "pydantic": os.path.join(layer_dir, "pydantic", "__init__.py"),
    }

    all_ok = True
    for module_name, module_path in critical_modules.items():
        if os.path.exists(module_path):
            print(f"✅ {module_name} 已安装")
        else:
            print(f"❌ {module_name} 未找到")
            all_ok = False

    if not all_ok:
        print("\n⚠️ 警告: 部分关键依赖未安装，可能导致运行时错误")

    # 打包依赖层
    print("\n打包依赖层...")
    zip_path = "layers/python-deps.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(layer_dir))
                zipf.write(file_path, arcname)

    # 检查包体积
    size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n✅ 依赖层打包完成: {zip_path}")
    print(f"   大小: {size:.2f} MB")

    if size > 100:
        print(f"⚠️  警告: 文件大小超过100MB限制!")
        print("   建议:")
        print("   1. 移除不必要的依赖")
        print("   2. 使用 --no-deps 参数精简安装")
        print("   3. 拆分为多个依赖层")
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
            zipf.write(handler_path, os.path.basename(handler_path))

        size = os.path.getsize(zip_path) / 1024
        print(f"✅ {zip_name}: {size:.2f} KB")

    return True


def verify_env_config():
    """验证环境配置"""
    print_step("3. 验证环境配置")

    required_vars = [
        "HUAWEI_CLOUD_AK",
        "HUAWEI_CLOUD_SK",
        "OBS_BUCKET_NAME",
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
        if not value or value.startswith('your_'):
            missing.append(var)
            print(f"❌ {var}: 未配置")
        else:
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
            print(f"✅ {var}: {masked}")

    if missing:
        print(f"\n⚠️  缺少配置: {', '.join(missing)}")
        print("   请在 .env 文件中配置这些变量")

    return True


def print_deployment_summary():
    """打印部署摘要"""
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
    print("   3. 创建4个函数并上传代码")
    print("   4. 配置环境变量和触发器")
    print("   5. 测试部署")


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║       Video Vault 依赖层打包工具 - 完整版               ║
║       包含所有直接依赖和传递依赖                         ║
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
