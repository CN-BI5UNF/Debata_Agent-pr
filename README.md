
# Debata_Agent

### **或许，`/v1/chat/completions`后面的，是个人？**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/binglang001/Debata_Agent/actions/workflows/test.yml)
[![WebUI](https://img.shields.io/badge/UI-WebUI%20%28FastAPI%29-blueviolet.svg)]
[![Stars](https://img.shields.io/github/stars/binglang001/Debata_Agent?style=social)](https://github.com/binglang001/Debata_Agent)

---

> 「虚拟角色不只是个会回复消息的程序，而是一个**真实的，能和你聊天的，有个性、有内心的**的人.」

框架名取自项目第一个被实现的角色 Debata. Debata_Agent 不绑定任何特定角色，你给它一个人格，它就活成那个人.

[![Debata 人设图](https://raw.githubusercontent.com/binglang001/Debata_Agent/main/personas/debata/角色人设主图.png)]

*Debata —— 17 岁，短黑发，灰色卫衣，对亲近的人毒舌，但心里十分在意.*

### 目录

- [差异](#与一般-ai-机器人的差异) · [功能(hyperlink)](docs/features.md) · [项目部署](#项目部署) · [项目结构](#项目结构) · [文档](#文档) · [设计决策](#设计决策) · [License](#license)
-----
## 与一般 AI 机器人的差异

| 维度  | 一般 AI  | Debata_Agent            |
|-----|--------|-------------------------|
| 上下文 | 每对话独立  | **全会话统一时间线 + 状态/关系上下文** |
| 回复  | 一条长消息  | 拆 3-7 条短消息，60% ≤12 字    |
| 节奏  | 永远秒回   | 可以「没看到」/「刚下课」/隔几小时回     |
| 边界  | 「好的！」  | 「？」 / 「嗯」 / 「6」 / 「算了」  |
| 风格  | 对所有人一样 | 对长辈/死党/陌生人**四种切换**      |
| 主动性 | 被动回复   | 自主判断要不要开口               |
| 配置  | 改代码    | **浏览器向导 + 设置页即时保存**     |

## 项目部署

### 环境要求

- **Python** 3.11 或更高
- **NapCat**  — QQ 协议端 注:[安装指南(hyperlink)](https://napneko.github.io/guide/start-install)
- **LLM API 密钥** — 推荐 DeepSeek（中文好、价格低、缓存命中后便宜）
- Windows / macOS / Linux 均可（浏览器控制台，无需图形环境；纯命令行跑 `--no-gui`）

### 部署命令 (各OS通用)

```bash
git clone https://github.com/binglang001/Debata_Agent.git
cd Debata_Agent
python -m pip install uv
uv sync
uv run main.py
```

启动后终端会打印**访问地址**和**访问令牌**，浏览器打开即可（默认监听 `0.0.0.0:8000`，局域网内任何设备都能访问）:

```
================================================================
  Debata_Agent WebUI 已启动
================================================================
  监听        : 0.0.0.0:8000
  访问地址    : http://127.0.0.1:8000
  访问地址    : http://192.168.1.23:8000
  访问令牌    : xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
================================================================
```

常用参数:

```bash
uv run main.py --port 9000          # 换端口
uv run main.py --host 127.0.0.1     # 只允许本机访问
uv run main.py --token 我的固定令牌   # 固定令牌，不自动生成
uv run main.py --no-auth            # 关闭鉴权（仅限完全可信内网）
uv run main.py --no-gui             # 纯命令行，不启动 WebUI
```

### 后台运行（systemd / tmux / screen）

长期运行推荐 systemd 用户服务，无需 sudo，崩溃自动重启、开机自启：

```bash
cd ~/Debata_Agent
bash scripts/install_systemd_user.sh
sudo loginctl enable-linger "$USER"   # 注销 SSH 后继续运行
systemctl --user status debata-agent --no-pager
journalctl --user -u debata-agent -f
```

默认同时启动 WebUI 和 QQ Runtime；只跑 headless 加 `--headless`。
临时挂机可以用 `tmux new -s debata` 或 `screen -S debata`。
NapCat 是独立进程，需要单独保持运行。

完整说明（系统级服务、nohup、升级、排错、安全建议）见
[后台运行指南](docs/background_running.md)。

本地 ASR/TTS/Embedding 的重依赖不随默认安装拉取; 打开对应模型的安装指引时，Debata 会检查缺失运行包并在后台用当前 venv 补装.

你也可以使用`uv sync --extra <你要的功能>`来提前安装，这与系统安装的效果相同，模块详见下表

### 可选模块

| 模块   | 做什么            | 需要什么                      |
|------|----------------|---------------------------|
| 视觉识别 | 看懂图片、提取文字、分析表情 | 多模态模型（GLM-4V / Qwen-VL 等） |
| 语音合成 | 用声音回复          | 本地 VoxCPM2 或云端 TTS        |
| 天气查询 | 查实时天气和预报       | 和风天气 API Key              |
| 联网搜索 | 搜实时信息          | 免费，走 DuckDuckGo           |

项目自带语音处理功能:QQ 语音转写使用 NapCat 内置功能.

### 首次配置（浏览器向导）

第一次启动时检测不到 `config.yaml`，WebUI 会直接给出配置页，填完即可用:
1. 选主模型（13 个内置预设，或自定义 OpenAI / Anthropic 兼容端点）
2. 选角色（内置 debata，或稍后在「角色」页导入 zip）
3. 接入 NapCat（连接模式 + 地址 + token + 入站策略）
4. 后台 Agent 开关（主动思考 / 滚动摘要 / 人格生成）

之后所有项目都能在「设置」页随时改，不需要重跑向导。

完成后进入仪表盘，常用配置能在设置页调整，无需再跑向导.

## 项目结构

```
Debata_Agent/
├── adapters/        渠道适配器（NapCat）
├── providers/       LLM 提供商（含 13 个预设 + 教程）
├── agents/          主聊天 / 主动思考 / 总结 / 人格生成 / 人格状态管理
├── mind/            人格状态 / 用户画像 / 亲近度 / 短期线索 / 后台审计存储
├── memory/          历史 + 重要记忆（文件 + RAG 向量）
├── tools/           AI 工具 + 装饰器注册
├── features/        视觉 / TTS / 天气 / 搜索 / Embedding
├── core/            事件总线 / 消息管道 / Runtime 生命周期
├── app_config/      配置 + AES/RSA 加密密钥
├── webui/           WebUI（FastAPI 后端 + 各页路由 + 静态前端）
├── plugins/         本地模型插件（TTS / Embedding）
├── personas/        人格目录（debata 入 git，其他 gitignore）
├── utils/           CQ 解析 / KV 缓存测量 / 时间
├── docs/            开发者文档
├── tests/           单元 / 集成测试
├── webui_server.py  WebUI 独立启动脚本
└── main.py          入口（默认启动 WebUI）
```

## 文档

- [图文教程](docs/getting_started.md) — 从零开始，截图指引每一步
- [角色编写指南](docs/persona_writing_guide.md) — 怎么写出会"活"的人格
- [架构总览](docs/architecture.md) — 模块依赖 + KV 缓存设计
- [后台运行指南](docs/background_running.md) — systemd / tmux / screen / nohup
- [KV 缓存基准](docs/kv_cache_benchmark.md) — 真实命中率数据
- [提供商开发](docs/provider_development.md) — 接新的 LLM
- [适配器开发](docs/adapter_development.md) — 接新的聊天平台
- [WebUI 说明](docs/webui.md) — 页面结构、接口一览、二次开发
- [UI 风格指南](docs/ui_style_guide.md) — 设计原则与配色规范

## 设计决策

几个不打算妥协的事:

- **单一 system + XML 分区**:稳定区前置，让 KV 缓存命中率 > 90%，省 token + 省延迟
- **「真人不完美」即合法**:不修跑题/改口/忘事，那不是 bug，是体感
- **加密密钥不要密码**:用户体验优先，密钥存 OS keyring + AES-GCM，密码学保证强度
- **常用配置尽量 UI 可改**:常用开关和密钥走设置页即时保存，Persona 文件仍然保留手写空间
- **黑名单优于白名单**:不想让 AI 接话的人点名拉黑即可，不必为此收紧整体开放策略

## License

[Apache 2.0](LICENSE) — 自由商用 / 修改 / 分发，保留版权与协议声明即可.

## 致谢

- [NapCat](https://github.com/NapNeko/NapCatQQ) — 现代 QQ 协议端
- [FastAPI](https://fastapi.tiangolo.com/) — WebUI 的 HTTP / WebSocket 框架
- [Uvicorn](https://www.uvicorn.org/) — ASGI 服务器
- DeepSeek / Anthropic / 智谱 等提供 LLM 服务

---



如果这个项目对你有用，欢迎给个 [Star](https://github.com/binglang001/Debata_Agent)，这对我们真的很重要，球球啦qwq