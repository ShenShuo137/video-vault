# 华为云原生环境依赖打包脚本（适配你的requirements.txt）
import os
import subprocess
import zipfile
import shutil
import glob
from obs import ObsClient

# ===================== 需替换为你的华为云配置 =====================
# 从环境变量读取（更安全）
AK = os.getenv("HUAWEI_CLOUD_AK", "HPUACBZNVJEWFWDF8ZEW")  # 设置默认值用于测试
SK = os.getenv("HUAWEI_CLOUD_SK", "PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu")
# OBS终端节点参考：https://developer.huaweicloud.com/endpoint?OBS
ENDPOINT = "https://obs.cn-north-4.myhuaweicloud.com"  # 替换为你的区域终端节点
BUCKET_NAME = "video-vault-storage"  # 提前创建好OBS桶，用于存储导出的依赖文件
# =================================================================

# 分批次安装依赖（按体积从小到大，减少单批次磁盘占用）
# 批次1：小体积基础依赖（<50MB）
DEPS_BATCH1 = [
    # 基础工具
    "crcmod", "six", "pytz", "certifi", "charset-normalizer", "idna", "urllib3",
    "pymysql", "python-dotenv", "colorlog", "tqdm", "jinja2",
    "python-dateutil", "typing-extensions",
    # 加密相关
    "pycryptodome", "cryptography",
]
# 批次2：中等体积依赖（50-100MB）
DEPS_BATCH2 = [
    # httpx 及其依赖
    "h11", "httpcore", "sniffio", "anyio", "httpx",
    # pydantic 及其依赖（openai 需要）
    "annotated-types", "pydantic-core", "pydantic",
    # 华为云 SDK
    "huaweicloudsdkcore", "huaweicloudsdkobs", "huaweicloudsdkocr",
    "huaweicloudsdkfunctiongraph", "huaweicloudsdkmpc", "esdk-obs-python",
    # Web 框架及依赖
    "click", "itsdangerous", "MarkupSafe", "Werkzeug",
    "Flask", "Flask-CORS", "requests",
    # AI 和其他
    "openai", "Pillow", "pytesseract",
]
# 批次3：大体积依赖（最后装，装完立即清理）
DEPS_BATCH3 = [
    # ⚠️ numpy 使用华为云运行时自带的版本，不打包（避免源码版本问题）
    # "numpy<2.0",
    "opencv-python-headless==4.8.1.78"  # 华为云环境有预编译wheel，直接安装
]

def get_pip_path():
    """适配华为云环境：优先使用 Python 3.9 的 pip"""
    print("=== 检测pip路径 ===")
    # 优先尝试 Python 3.9 的 pip（关键！）
    pip_paths = [
        "python3.9 -m pip",  # 方式1：通过 python3.9 模块调用
        "/usr/bin/python3.9 -m pip",  # 方式2：绝对路径
        "pip3.9",  # 方式3：直接调用 pip3.9
        "/usr/local/bin/pip3.9",
        "/usr/bin/pip3.9",
        "pip3",  # 最后才尝试默认 pip3
    ]
    for pip_cmd in pip_paths:
        try:
            # 检查版本
            result = subprocess.run(
                pip_cmd.split() + ["--version"],
                capture_output=True,
                text=True,
                check=True
            )
            # 检查是否是 Python 3.9
            if "python 3.9" in result.stdout.lower() or "python3.9" in result.stdout.lower():
                print(f"✅ 找到 Python 3.9 pip：{pip_cmd}")
                print(f"   版本信息：{result.stdout.strip()}")
                return pip_cmd.split()  # 返回列表形式（支持 python3.9 -m pip）
        except Exception:
            continue

    # 如果找不到 Python 3.9，打印警告并使用默认 pip3
    print("⚠️  警告：未找到 Python 3.9 的 pip，使用默认 pip3")
    print("   这可能导致依赖不兼容 Python 3.9 运行时！")
    return ["pip3"]

def clean_temp_files(target_dir, pip_cmd):
    """清理临时文件（降低磁盘占用）"""
    print("=== 清理临时文件 ===")
    # 1. 清理pip缓存
    subprocess.run(pip_cmd + ["cache", "purge"], capture_output=True)
    # 2. 清理__pycache__目录
    for cache_dir in glob.glob(os.path.join(target_dir, "**/__pycache__"), recursive=True):
        shutil.rmtree(cache_dir, ignore_errors=True)
    # 3. 清理编译临时文件（.so/.o等）
    for tmp_file in glob.glob(os.path.join(target_dir, "**/*.so"), recursive=True):
        if "test" in tmp_file or "example" in tmp_file:
            os.remove(tmp_file)
    # 4. 清理压缩包/缓存文件
    for tmp_suffix in [".whl", ".tar.gz", ".zip"]:
        for tmp_file in glob.glob(os.path.join("/tmp", f"*{tmp_suffix}")):
            os.remove(tmp_file)
    print("=== 临时文件清理完成 ===")

def install_deps_batch(pip_cmd, target_dir, deps_batch, batch_name):
    """分批次安装依赖"""
    print(f"=== 安装{batch_name}依赖 ===")
    install_cmd = pip_cmd + [
        "install",
        "--target", target_dir,
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
        "--upgrade",
        "--no-cache-dir",  # 禁用pip缓存（关键：减少磁盘占用）
        "--no-build-isolation"  # 禁用构建隔离（减少临时文件）
    ] + deps_batch
    
    result = subprocess.run(
        install_cmd, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise Exception(f"{batch_name}依赖安装失败：{result.stderr}")
    
    # 每装完一批，立即清理临时文件
    clean_temp_files(target_dir, pip_cmd)
    # 打印当前磁盘占用
    disk_usage = subprocess.run(
        ["df", "-h", "/tmp"], capture_output=True, text=True
    )
    print(f"=== {batch_name}安装后磁盘占用：\n{disk_usage.stdout} ===")

def install_dependencies(pip_cmd):
    """分批次安装依赖（核心：降低单批次磁盘占用）"""
    print("=== 开始分批次安装依赖 ===")
    target_dir = "/tmp/python_deps"
    os.makedirs(target_dir, exist_ok=True)

    # 批次1：小体积依赖（<50MB）
    install_deps_batch(pip_cmd, target_dir, DEPS_BATCH1, "批次1（小体积）")
    # 批次2：中等体积依赖（50-100MB）
    install_deps_batch(pip_cmd, target_dir, DEPS_BATCH2, "批次2（中等体积）")
    # 批次3：大体积依赖（最后装，装完立即清理）
    install_deps_batch(pip_cmd, target_dir, DEPS_BATCH3, "批次3（大体积）")

    print(f"=== 所有依赖安装完成，安装目录：{target_dir} ===")
    return target_dir

def export_requirements(target_dir, pip_cmd):
    """导出华为云环境实际安装的依赖清单"""
    print("=== 导出requirements.txt ===")
    req_path = "/tmp/requirements_huaweiyun.txt"
    freeze_cmd = pip_cmd + ["freeze", "--path", target_dir]
    freeze_result = subprocess.run(
        freeze_cmd, capture_output=True, text=True, encoding="utf-8"
    )
    with open(req_path, "w", encoding="utf-8") as f:
        f.write(freeze_result.stdout)
    print(f"=== requirements.txt已保存：{req_path} ===")
    return req_path

def extract_shared_from_obs():
    """从OBS已有的依赖层中提取shared/代码"""
    print("=== 从OBS下载旧依赖层提取shared/代码 ===")

    obs_client = ObsClient(
        access_key_id=AK, secret_access_key=SK, server=ENDPOINT
    )

    # 旧依赖层的对象键
    old_layer_key = "python-deps.zip"
    old_layer_path = "/tmp/old_layer.zip"

    print(f"   下载: obs://{BUCKET_NAME}/{old_layer_key}")
    try:
        resp = obs_client.getObject(BUCKET_NAME, old_layer_key, downloadPath=old_layer_path)
        if resp.status >= 300:
            print(f"⚠️  下载失败: {resp.errorMessage}")
            print("   将跳过shared/代码打包")
            return None
        print(f"   ✅ 下载成功")
    except Exception as e:
        print(f"⚠️  下载失败: {e}")
        print("   将跳过shared/代码打包")
        return None

    # 解压并提取 shared/ 目录
    print("   解压依赖层...")
    extract_dir = "/tmp/old_extract"
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(old_layer_path, "r") as zf:
        # 旧依赖层结构: python/shared/...
        shared_files = [f for f in zf.namelist() if f.startswith("python/shared/")]

        if not shared_files:
            print("⚠️  警告: 旧依赖层中未找到python/shared/目录")
            return None

        print(f"   找到 {len(shared_files)} 个shared/文件")

        # 解压 shared/ 相关文件
        for file in shared_files:
            zf.extract(file, extract_dir)

    shared_path = os.path.join(extract_dir, "python", "shared")
    if os.path.exists(shared_path):
        print(f"   ✅ shared/代码已提取到: {shared_path}")
        return shared_path
    else:
        print("⚠️  警告: 提取失败，未找到shared/目录")
        return None


def package_dependencies(target_dir, pip_cmd):
    """打包依赖包（精简体积）"""
    print("=== 打包依赖包 ===")
    zip_path = "/tmp/python_deps_huaweiyun.zip"

    # 打包前最后清理一次临时文件
    clean_temp_files(target_dir, pip_cmd)

    # ⚠️ 新增：从OBS旧依赖层提取shared/代码
    shared_src = extract_shared_from_obs()
    if shared_src:
        shared_dst = os.path.join(target_dir, "shared")

        # 如果目标已存在，先删除
        if os.path.exists(shared_dst):
            shutil.rmtree(shared_dst)

        # 复制整个 shared 目录
        shutil.copytree(shared_src, shared_dst)
        print(f"✅ shared/ 目录已复制到依赖包中")
    else:
        print("⚠️  跳过shared/代码打包")

    # 打包（仅保留必需文件，跳过测试/示例/缓存）
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(target_dir):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if d not in ["__pycache__", "test", "tests", "example", "examples"]]
            for file in files:
                if file.endswith((".pyc", ".pyo", ".tmp", ".log")):
                    continue
                file_abs_path = os.path.join(root, file)
                zip_rel_path = os.path.join("python", os.path.relpath(file_abs_path, target_dir))
                zf.write(file_abs_path, zip_rel_path)

    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"=== 依赖包打包完成：{zip_path}（大小：{zip_size:.2f} MB）===")
    if zip_size > 100:
        print("⚠️ 警告：依赖包体积超过100MB，需精简！")
    return zip_path

def upload_to_obs(local_path, obs_key):
    """上传文件到OBS"""
    print(f"=== 上传文件到OBS：{local_path} ===")
    obs_client = ObsClient(
        access_key_id=AK, secret_access_key=SK, server=ENDPOINT
    )
    resp = obs_client.putFile(BUCKET_NAME, obs_key, local_path)
    if resp.status >= 300:
        raise Exception(f"OBS上传失败：{resp.errorMessage}")
    print(f"=== OBS上传成功！===")

def handler(event, context):
    """华为云函数入口"""
    try:
        # 获取 pip 命令（确保是 Python 3.9）
        pip_cmd = get_pip_path()

        # 1. 分批次安装依赖（核心：解决磁盘超限）
        deps_dir = install_dependencies(pip_cmd)
        # 2. 导出requirements.txt
        req_file = export_requirements(deps_dir, pip_cmd)
        # 3. 打包依赖包
        zip_file = package_dependencies(deps_dir, pip_cmd)
        # 4. 上传到OBS
        upload_to_obs(req_file, "deps/requirements_huaweiyun.txt")
        upload_to_obs(zip_file, "deps/python_deps_huaweiyun.zip")
        
        return {
            "status": "success",
            "message": "依赖打包完成！",
            "requirements_obs_path": f"obs://{BUCKET_NAME}/deps/requirements_huaweiyun.txt",
            "deps_zip_obs_path": f"obs://{BUCKET_NAME}/deps/python_deps_huaweiyun.zip"
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "tips": "请检查依赖批次/清理逻辑，或精简大体积依赖"
        }