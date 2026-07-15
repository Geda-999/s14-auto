# Git 提交日期修改器
# 用法: python git_date_modifier.py <commit_sha> <date_string> [--repo <path>]

# 修改指定提交的作者日期和提交日期。
# 需要 git-filter-repo (通过 pip install git-filter-repo 安装)

import argparse
import subprocess
import sys
import os
from datetime import datetime

def run_git_command(cmd, cwd=None):
    """运行 git 命令并返回其输出作为字符串。"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git 命令失败: {' '.join(cmd)}")
        print(f"错误: {e.stderr}")
        sys.exit(1)

def is_git_repo(path):
    """检查给定路径是否为 git 仓库。"""
    try:
        run_git_command(['git', 'rev-parse', '--is-inside-work-tree'], cwd=path)
        return True
    except SystemExit:
        return False

def get_full_sha(repo_path, short_sha):
    """将短 SHA 转换为完整 SHA。"""
    try:
        full_sha = run_git_command(['git', 'rev-parse', short_sha], cwd=repo_path)
        return full_sha
    except SystemExit:
        print(f"错误: 无效的提交 SHA: {short_sha}")
        sys.exit(1)

def validate_date_string(date_str):
    """验证并规范化日期字符串。"""
    # 尝试格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DDTHH:MM:SS
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            dt = datetime.strptime(date_str, fmt)
            # 返回带 'T' 的标准化格式，用于 filter-repo 回调
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        except ValueError:
            pass
    print(f"错误: 无效的日期格式。请使用 'YYYY-MM-DD HH:MM:SS' 或 'YYYY-MM-DDTHH:MM:SS'")
    sys.exit(1)

def check_git_filter_repo():
    """检查 git-filter-repo 是否已安装，如果未安装则尝试安装。"""
    try:
        subprocess.run(['git', 'filter-repo', '--version'], check=True, capture_output=True)
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("git-filter-repo 未安装。正在尝试安装...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'git-filter-repo'], check=True)
            print("成功安装 git-filter-repo。")
        except subprocess.CalledProcessError as e:
            print(f"安装 git-filter-repo 失败: {e}")
            print("请手动安装: pip install git-filter-repo")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="修改 Git 提交日期。")
    parser.add_argument('commit_sha', help='要修改的提交 SHA（完整或短格式）')
    parser.add_argument('date_str', help='新日期（格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DDTHH:MM:SS）')
    parser.add_argument('--repo', default='.', help='git 仓库路径（默认: 当前目录）')
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    if not os.path.isdir(repo_path):
        print(f"错误: 仓库路径不存在: {repo_path}")
        sys.exit(1)

    if not is_git_repo(repo_path):
        print(f"错误: 不是 git 仓库: {repo_path}")
        sys.exit(1)

    # 检查 git-filter-repo
    check_git_filter_repo()

    # 获取完整 SHA
    full_sha = get_full_sha(repo_path, args.commit_sha)
    print(f"使用完整提交 SHA: {full_sha}")

    # 验证并规范化日期字符串
    normalized_date = validate_date_string(args.date_str)
    print(f"使用规范化日期: {normalized_date}")

    # 创建备份分支
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_branch = f'backup_{timestamp}'
    try:
        run_git_command(['git', 'branch', backup_branch], cwd=repo_path)
        print(f"创建备份分支: {backup_branch}")
    except SystemExit:
        print(f"警告: 无法创建备份分支 '{backup_branch}'. 它可能已经存在。")

    # 准备 filter-repo 回调
    # 注意: commit.original_id 是原始提交 ID 的十六进制字符串（字节）
    callback = f"if commit.original_id == b'{full_sha}': commit.date = b'{normalized_date}'"
    print(f"运行 git filter-repo，回调: {callback}")

    # 运行 filter-repo
    try:
        subprocess.run([
            'git', 'filter-repo',
            '--force',
            '--commit-callback', callback,
            '--', 'HEAD'
        ], cwd=repo_path, check=True)
        print("成功更新提交日期。")
        print(f"要恢复，请运行: git checkout {backup_branch} && git branch -D main && git checkout -b main {backup_branch}")
    except subprocess.CalledProcessError as e:
        print(f"运行 git filter-repo 时出错: {e}")
        print(f"您可以从备份分支恢复: {backup_branch}")
        sys.exit(1)

if __name__ == '__main__':
    main()
