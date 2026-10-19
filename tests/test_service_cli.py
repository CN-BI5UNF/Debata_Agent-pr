"""简化服务命令测试（不触碰真实 systemd）。"""

from __future__ import annotations

from types import SimpleNamespace

import service_cli


def test_help_lists_short_commands(capsys):
    assert service_cli.main(["help"]) == 0
    output = capsys.readouterr().out
    for command in ("start", "stop", "restart", "status", "log", "enable", "disable"):
        assert f"debata {command}" in output


def test_unknown_command_returns_2(capsys):
    assert service_cli.main(["nope"]) == 2
    assert "未知命令" in capsys.readouterr().out


def test_start_calls_systemctl_start(monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.setattr(service_cli, "_systemd_ready", lambda: True)
    monkeypatch.setattr(service_cli, "_ensure_installed", lambda: True)
    monkeypatch.setattr(
        service_cli,
        "_run",
        lambda command: calls.append(command) or 0,
    )

    assert service_cli.main(["start"]) == 0
    assert calls == [["systemctl", "--user", "start", "debata-agent"]]


def test_enable_runs_enable_start_and_linger(monkeypatch):
    calls: list[list[str]] = []
    linger_calls: list[list[str]] = []
    monkeypatch.setattr(service_cli, "_systemd_ready", lambda: True)
    monkeypatch.setattr(service_cli, "_ensure_installed", lambda: True)
    monkeypatch.setattr(
        service_cli,
        "_run",
        lambda command: calls.append(command) or 0,
    )
    monkeypatch.setattr(
        service_cli.shutil,
        "which",
        lambda name: f"/usr/bin/{name}",
    )

    def fake_run(command, **_kwargs):
        linger_calls.append(list(command))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(service_cli.subprocess, "run", fake_run)

    assert service_cli.main(["enable"]) == 0
    assert ["systemctl", "--user", "enable", "debata-agent"] in calls
    assert ["systemctl", "--user", "start", "debata-agent"] in calls
    assert linger_calls
    assert linger_calls[0][:2] == ["loginctl", "enable-linger"]


def test_disable_only_disables_autostart(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    unit_file = tmp_path / "debata-agent.service"
    unit_file.write_text("[Unit]\n", encoding="utf-8")
    monkeypatch.setattr(service_cli, "UNIT_FILE", unit_file)
    monkeypatch.setattr(service_cli, "_systemd_ready", lambda: True)
    monkeypatch.setattr(
        service_cli,
        "_run",
        lambda command: calls.append(command) or 0,
    )

    assert service_cli.main(["disable"]) == 0
    assert calls == [["systemctl", "--user", "disable", "debata-agent"]]


def test_log_uses_system_journal_when_user_journal_is_missing(monkeypatch):
    monkeypatch.setattr(
        service_cli.shutil, "which", lambda name: f"/usr/bin/{name}"
    )

    def fake_run(command, **_kwargs):
        if "--user" in command:
            return SimpleNamespace(
                returncode=0,
                stdout="",
                stderr="No journal files were found.\n",
            )
        return SimpleNamespace(
            returncode=0,
            stdout="Oct 20 00:00:00 host python[1]: hello\n",
            stderr="",
        )

    monkeypatch.setattr(service_cli.subprocess, "run", fake_run)

    command = service_cli._journal_command()

    assert command is not None
    assert "_SYSTEMD_USER_UNIT=debata-agent.service" in command
    assert command[-1] == "-f"


def test_log_falls_back_to_app_log_file(monkeypatch, tmp_path, capsys):
    log_file = tmp_path / "debata.log"
    log_file.write_text("hello\n", encoding="utf-8")
    calls: list[list[str]] = []

    monkeypatch.setattr(service_cli, "UNIT_FILE", tmp_path / "unit")
    (tmp_path / "unit").write_text("[Unit]\n", encoding="utf-8")
    monkeypatch.setattr(service_cli, "_journal_command", lambda: None)
    monkeypatch.setattr(service_cli, "_app_log_path", lambda: log_file)
    monkeypatch.setattr(
        service_cli,
        "_run",
        lambda command: calls.append(command) or 0,
    )

    assert service_cli.main(["log"]) == 0
    assert calls == [["tail", "-n", "200", "-F", str(log_file)]]
    assert "debata.log" in capsys.readouterr().out
