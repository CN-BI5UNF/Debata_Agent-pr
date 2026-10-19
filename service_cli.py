"""Debata 后台服务管理命令。

用法::

    debata start       启动（首次会自动安装 systemd 用户服务）
    debata stop        停止
    debata restart     重启
    debata status      查看状态
    debata log         实时查看日志
    debata enable      设置开机自启（并立即启动）
    debata disable     取消开机自启
    debata install     只安装服务，不启动
    debata uninstall   卸载服务
    debata help        查看帮助

底层仍然是 systemd 用户服务，只是把 systemctl/journalctl 的参数收进了一个
和 ``pnpm start/stop/log`` 类似的管理命令里。
"""

from __future__ import annotations

import getpass
import os
import shutil
import subprocess
import sys
from pathlib import Path

SERVICE_NAME = "debata-agent"
PROJECT_ROOT = Path(__file__).resolve().parent
UNIT_DIR = Path(
    os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
) / "systemd" / "user"
UNIT_FILE = UNIT_DIR / f"{SERVICE_NAME}.service"
INSTALLER = PROJECT_ROOT / "scripts" / "install_systemd_user.sh"
LAUNCHER = Path.home() / ".local" / "bin" / "debata"
LAUNCHER_MARKER = "# Debata Agent launcher"

COMMANDS = (
    "start",
    "stop",
    "restart",
    "status",
    "log",
    "enable",
    "disable",
    "install",
    "uninstall",
    "help",
)

HELP = """Debata 后台服务管理

用法:
  debata start       启动（首次会自动安装服务）
  debata stop        停止
  debata restart     重启
  debata status      查看状态
  debata log         实时查看日志（Ctrl+C 退出）
  debata enable      设置开机自启（并立即启动）
  debata disable     取消开机自启
  debata install     只安装服务，不启动
  debata uninstall   卸载服务
  debata help        显示本帮助

说明:
  - 底层使用 systemd 用户服务，不需要 sudo。
  - 如果提示 linger 失败，执行: sudo loginctl enable-linger $USER
  - 自定义端口 / headless:
      bash scripts/install_systemd_user.sh --port 9000
      bash scripts/install_systemd_user.sh --headless
  - 完整文档: docs/background_running.md
"""


def _systemctl(*args: str) -> list[str]:
    return ["systemctl", "--user", SERVICE_NAME, *args]


def _run(command: list[str]) -> int:
    try:
        return subprocess.call(command)
    except FileNotFoundError:
        print(f"命令不存在: {command[0]}")
        return 127
    except KeyboardInterrupt:
        return 130


def _systemd_ready() -> bool:
    if shutil.which("systemctl") is None:
        print(
            "当前系统没有 systemd。请改用 tmux / screen / nohup，"
            "见 docs/background_running.md。"
        )
        return False
    return True


def _require_unit() -> bool:
    if UNIT_FILE.exists():
        return True
    print("服务尚未安装。先运行: debata start")
    return False


def _ensure_installed() -> bool:
    """服务不存在时自动调用安装脚本，只写 unit，不启动。"""
    if UNIT_FILE.exists():
        return True
    if not INSTALLER.exists():
        print(f"找不到安装脚本: {INSTALLER}")
        return False
    print("首次使用，正在安装 systemd 服务...")
    return_code = _run(["bash", str(INSTALLER), "--write-only"])
    if return_code != 0 or not UNIT_FILE.exists():
        print("服务安装失败。可手动运行: bash scripts/install_systemd_user.sh")
        return False
    return True


def _token_path() -> Path:
    data_root = Path(
        os.environ.get("DEBATA_DATA_ROOT")
        or (Path.home() / ".local" / "share" / "Debata_Agent")
    )
    return data_root / "instances" / "default" / "webui_token.txt"


def cmd_start() -> int:
    if not _systemd_ready() or not _ensure_installed():
        return 1
    return_code = _run(_systemctl("start"))
    if return_code == 0:
        print("已启动 debata-agent。")
        print("日志: debata log")
        print(f"WebUI 令牌: {_token_path()}（首次启动后生成）")
    else:
        print("启动失败。运行 debata log 查看原因。")
    return return_code


def cmd_stop() -> int:
    if not _systemd_ready() or not _require_unit():
        return 1
    return_code = _run(_systemctl("stop"))
    if return_code == 0:
        print("已停止 debata-agent。")
    return return_code


def cmd_restart() -> int:
    if not _systemd_ready() or not _ensure_installed():
        return 1
    return_code = _run(_systemctl("restart"))
    if return_code == 0:
        print("已重启 debata-agent。")
    else:
        print("重启失败。运行 debata log 查看原因。")
    return return_code


def cmd_status() -> int:
    if not _systemd_ready() or not _require_unit():
        return 1
    return _run(["systemctl", "--user", "status", SERVICE_NAME, "--no-pager"])


def cmd_log() -> int:
    if not _require_unit():
        return 1
    if shutil.which("journalctl") is None:
        print("当前系统没有 journalctl。日志见数据目录的 logs/debata.log。")
        return 1
    return _run(["journalctl", "--user", "-u", SERVICE_NAME, "-n", "200", "-f"])


def _enable_linger() -> bool:
    user = os.environ.get("USER") or getpass.getuser()
    if shutil.which("loginctl") is None:
        print(f"提示：请手动执行 sudo loginctl enable-linger {user}")
        return False
    result = subprocess.run(
        ["loginctl", "enable-linger", user],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("已开启 linger：注销 SSH 后服务仍会运行。")
        return True
    print(f"提示：请执行 sudo loginctl enable-linger {user}")
    print("      否则注销/重启后服务可能不会继续运行。")
    return False


def cmd_enable() -> int:
    if not _systemd_ready() or not _ensure_installed():
        return 1
    return_code = _run(["systemctl", "--user", "enable", SERVICE_NAME])
    if return_code != 0:
        print("设置开机自启失败。")
        return return_code
    start_code = _run(_systemctl("start"))
    _enable_linger()
    print("已设置开机自启：debata-agent")
    if start_code != 0:
        print("当前启动失败；运行 debata log 查看原因。")
    return 0


def cmd_disable() -> int:
    if not _systemd_ready():
        return 1
    if not UNIT_FILE.exists():
        print("服务尚未安装。")
        return 1
    return_code = _run(["systemctl", "--user", "disable", SERVICE_NAME])
    if return_code == 0:
        print("已取消开机自启。")
        print("当前进程仍在运行；停止用: debata stop")
    return return_code


def cmd_install() -> int:
    if not _systemd_ready() or not _ensure_installed():
        return 1
    print(f"服务已安装: {UNIT_FILE}")
    print("启动: debata start")
    return 0


def cmd_uninstall() -> int:
    if not UNIT_FILE.exists():
        print("服务未安装。")
    else:
        _run(["systemctl", "--user", "disable", "--now", SERVICE_NAME])
        try:
            UNIT_FILE.unlink()
        except OSError as exc:
            print(f"删除 unit 失败: {exc}")
            return 1
        _run(["systemctl", "--user", "daemon-reload"])
        print("已卸载 debata-agent 服务。")

    if LAUNCHER.exists():
        try:
            content = LAUNCHER.read_text(encoding="utf-8", errors="ignore")
            if LAUNCHER_MARKER in content:
                LAUNCHER.unlink()
                print(f"已移除命令: {LAUNCHER}")
        except OSError:
            pass
    return 0


_DISPATCH = {
    "start": cmd_start,
    "stop": cmd_stop,
    "restart": cmd_restart,
    "status": cmd_status,
    "log": cmd_log,
    "enable": cmd_enable,
    "disable": cmd_disable,
    "install": cmd_install,
    "uninstall": cmd_uninstall,
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("help", "-h", "--help"):
        print(HELP)
        return 0
    command = args[0]
    handler = _DISPATCH.get(command)
    if handler is None:
        print(f"未知命令: {command}\n")
        print(HELP)
        return 2
    return handler()


__all__ = ["COMMANDS", "SERVICE_NAME", "main"]
