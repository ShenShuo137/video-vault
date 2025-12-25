#!/usr/bin/env python3
"""
Video Vault 依赖层打包脚本 - 修复版
解决 numpy 源码导入问题
"""

import os
import sys
import subprocess
import shutil
import zipfile


def print_step(step_name):
    """打印步骤标题"""
    print("\n" + "=" * 60)
    print(f"  {step_name}")
    print("=" * 60)


def check_python_version():
    """检查Python版本"""
    version_info = sys.version_info
    if version_info < (3, 9):
        print(f"⚠️  警告: 当前Python版本 {version_info.major}.{version_info.minor}")
        print("   推荐使用 Python 3.9 与华为云环境一致")


def create_dependency_layer():
    """创建依赖层 - 强制使用预编译 wheel"""
    print_step("1. 创建依赖层（强制使用 manylinux wheel）")

    check_python_version()

    # 清理旧文件
    layer_root = "layers"
    if os.path.exists(layer_root):
        print("清理旧的依赖层目录...")
        shutil.rmtree(layer_root)

    # 创建目录
    layer_dir = "layers/python-deps"
    os.makedirs(layer_dir, exist_ok=True)

    # 华为云 FunctionGraph 依赖
    packages = [
        "opencv-python-headless==4.8.1.78",  # 无头版本，更小
        "numpy==1.24.3",                      # 兼容 Python 3.9
        "Pillow==10.0.0",
        "pytesseract==0.3.10",
        "esdk-obs-python==3.22.2",
        "huaweicloud-sdk-core==3.1.53",
        "huaweicloud-sdk-functiongraph==3.1.53",
        "requests==2.31.0",
        "pymysql==1.1.0",
        "cryptography==41.0.3",
        "python-dotenv==1.0.0"
    ]

    print("\n安装依赖包（强制使用预编译 wheel）...")
    print("目标平台: Linux x86_64 (manylinux2014)")
    print("Python 版本: 3.9")

    # 关键参数：
    # --platform: 指定目标平台（华为云是 Linux x86_64）
    # --only-binary=:all: 只接受预编译的 wheel，拒绝源码
    # --python-version: Python 版本
    # --implementation: CPython
    cmd = [
        sys.executable, "-m", "pip", "install",
        "-t", layer_dir,
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:",
        "--python-version", "39",
        "--implementation", "cp",
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
        "--no-cache-dir"
    ] + packages

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 依赖安装失败: {e}")
        print("\n可能原因：")
        print("1. 某些包没有 manylinux wheel（尝试去掉 --only-binary）")
        print("2. 网络问题（尝试切换镜像源）")
        return False

    # 复制 shared 代码
    print("\n复制项目代码...")
    if os.path.exists("shared"):
        shutil.copytree("shared", os.path.join(layer_dir, "shared"), dirs_exist_ok=True)
        print("✅ shared/ 目录已复制")
    else:
        print("⚠️  警告: shared/ 目录不存在")
        return False

    # 清理不必要的文件（减小体积）
    print("\n清理不必要的文件...")
    patterns_to_remove = [
        "*.pyc", "*.pyo", "__pycache__", "*.dist-info",
        "*.egg-info", "tests", "test", "*.so.debug"
    ]

    for root, dirs, files in os.walk(layer_dir):
        # 删除目录
        for pattern in ["__pycache__", "tests", "test", "*.dist-info", "*.egg-info"]:
            if pattern.startswith("*."):
                continue
            if pattern in dirs:
                try:
                    shutil.rmtree(os.path.join(root, pattern))
                except Exception:
                    pass

        # 删除文件
        for file in files:
            if file.endswith(('.pyc', '.pyo', '.so.debug')):
                try:
                    os.remove(os.path.join(root, file))
                except Exception:
                    pass

    # 验证 numpy 安装
    print("\n验证 numpy 安装...")
    numpy_init = os.path.join(layer_dir, "numpy", "__init__.py")
    if os.path.exists(numpy_init):
        with open(numpy_init, 'r', encoding='utf-8') as f:
            content = f.read()
            if "raise ImportError(msg)" in content and "source directory" in content:
                print("⚠️  检测到 numpy 源码版本，这会导致导入失败！")
                print("   尝试使用 Docker 或在 Linux 环境打包")
            else:
                print("✅ numpy 看起来是预编译版本")
    else:
        print("⚠️  未找到 numpy")

    # 打包
    print("\n打包依赖层...")
    zip_path = "layers/python-deps.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, layer_dir)
                zipf.write(file_path, arcname)

    size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n✅ 依赖层打包完成: {zip_path}")
    print(f"   大小: {size:.2f} MB")

    if size > 100:
        print(f"⚠️  警告: 超过 100MB 限制!")
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
            # 只打包 handler 文件
            zipf.write(handler_path, os.path.basename(handler_path))

        size = os.path.getsize(zip_path) / 1024
        print(f"✅ {zip_name}: {size:.2f} KB")

    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Video Vault 依赖打包工具 - 修复版")
    print("  目标: 华为云 FunctionGraph (Python 3.9, Linux x86_64)")
    print("=" * 60)

    # 创建依赖层
    if not create_dependency_layer():
        print("\n❌ 依赖层创建失败")
        return False

    # 打包函数
    if not create_function_packages():
        print("\n❌ 函数打包失败")
        return False

    print("\n" + "=" * 60)
    print("  ✅ 打包完成")
    print("=" * 60)
    print("\n📦 产物:")
    print("   layers/python-deps.zip  - 依赖层")
    print("   deploy/*.zip            - 函数代码")
    print("\n📚 部署步骤:")
    print("   1. 上传 python-deps.zip 到华为云依赖层")
    print("   2. 上传 deploy/*.zip 到对应函数")
    print("   3. 在每个函数中挂载依赖层")
    print("   4. 配置环境变量")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
