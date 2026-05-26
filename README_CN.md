# ScanCodex

> 面向 AI 智能体的安全扫描工具知识库 — 数据来源于 [Scanners-Box](https://github.com/We5ter/Scanners-Box)。

ScanCodex 是一个 MCP（模型上下文协议）服务，将 Scanners-Box 收录的 300+ 款开源安全工具转化为可查询的知识库，供 Claude、Cursor 及任何兼容 MCP 的 AI 智能体使用。

只需告诉 AI _"扫描 Kubernetes 集群的安全配置用什么工具？"_，它就会查询知识库、推荐合适的工具、展示安装和使用方法，甚至帮你一键安装。

## 暴露的工具

| 工具 | 描述 |
|------|------|
| `list_categories` | 浏览全部 20 个扫描器分类 |
| `recommend_scanners` | 按任务描述、分类或编程语言查找扫描器 |
| `build_workflow` | 获取某个渗透测试阶段的完整工具链 |
| `get_tool_usage` | 从工具的 GitHub README 获取安装与使用说明 |
| `install_tool` | 一键克隆并安装指定工具到本地 |

## 快速开始

**环境要求：** Python 3.10+

```bash
git clone https://github.com/We5ter/ScanCodex
cd ScanCodex
pip install .
```

首次使用时，Scanners-Box 数据会**自动下载**并缓存到 `~/.cache/scancodex/`，无需手动克隆额外仓库。

## Claude Desktop 配置

在 `~/Library/Application Support/Claude/claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "scancodex": {
      "command": "python3",
      "args": ["-m", "scancodex.server"]
    }
  }
}
```

## Claude Code 配置

```bash
claude mcp add scancodex -- python3 -m scancodex.server
```

## 示例提问

```
测试 LLM 应用的提示词注入漏洞用什么工具？

扫描 Kubernetes 集群的安全问题有哪些推荐工具？

帮我生成一套渗透测试侦查阶段的工具链。

有哪些 Go 语言编写的容器镜像漏洞扫描器？

GitHack 怎么安装和使用？

帮我安装 subfinder。
```

## build_workflow 支持的渗透阶段

`recon` · `vuln_scan` · `web` · `container` · `mobile` · `smart_contract` · `ai_apps` · `malware` · `code_analysis` · `incident` · `a3c`

## 许可证

MIT — 数据来源于 [Scanners-Box](https://github.com/We5ter/Scanners-Box)（CC-BY-NC-ND-4.0）。
