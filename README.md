# DeepSOC 🚀

<p align="center">
  <strong>AI驱动的新一代安全运营中心 | AI-Powered Security Operations Center</strong>
</p>

<p align="center">
  <a href="https://github.com/flagify-com/deepsoc/stargazers">
    <img src="https://img.shields.io/github/stars/flagify-com/deepsoc" alt="Stars">
  </a>
  <a href="https://github.com/flagify-com/deepsoc/network/members">
    <img src="https://img.shields.io/github/forks/flagify-com/deepsoc" alt="Forks">
  </a>
  <a href="https://github.com/flagify-com/deepsoc/issues">
    <img src="https://img.shields.io/github/issues/flagify-com/deepsoc" alt="Issues">
  </a>
  <a href="https://github.com/flagify-com/deepsoc/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/flagify-com/deepsoc" alt="License">
  </a>
</p>

## 📖 项目简介

DeepSOC 是一个革命性的安全运营解决方案，它将先进的 AI 技术与传统的安全运营工具完美结合，通过多智能体（Multi-Agent）架构，DeepSOC 能够自动化处理安全事件，显著提升安全运营效率。

<h2>注意，体验产品最新功能，请访问项目DEV分支。</h2>

[DeepSOC DEV分支](https://github.com/flagify-com/deepsoc/tree/dev)


DeepSOC产品工作逻辑图

![DeepSOC产品工作逻辑图](app/static/images/deepsoc-work-logic.jpg)

### ✨ 核心特性

- 🤖 **智能多Agent架构**
  - 指挥官：统筹全局决策
  - 经理：任务分配协调
  - 操作员：执行具体操作
  - 执行器：连接外部工具
  - 专家：提供专业建议

- 🔄 **自动化处理流程**
  - 自动分析安全告警
  - 智能决策响应方案
  - 自动化执行处置
  - 实时反馈处理结果

- 🛠 **丰富的工具集成**
  - 支持 SOAR 自动化编排
  - 可扩展 Function Calling Tools
  - 可扩展 MCP Tools
  - 支持人工参与事件处置

- 🌐 **开放式架构**
  - 支持自定义 AI 参数
  - 可自定义处理流程
  - 灵活的 API 接口
  - WebSocket 实时通信

## 🚀 快速开始

### 环境要求

- Python 3.8+
- SQLite（试验阶段方便部署测试，成熟之后随时切换）
- 自动化系统（支持SOAR编排自动化系统，推荐[OctoMation社区免费版](https://github.com/flagify-com/OctoMation)）
  - [剧本配置信息](docs/soar-config-help.md)


### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/flagify-com/deepsoc.git
cd deepsoc
```

2. 安装依赖
```bash
virtualenv venv
source venv/bin/activate
# Windows
# .\venv\Scripts\activate
pip install -r requirements.txt
# pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com 
# pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple --trusted-host mirrors.cloud.tencent.com

```

3. 配置环境变量
```bash
cp sample.env .env
# 编辑 .env 文件，配置必要的环境变量
```

4. 启动服务

为了方便管理，调试和优化改进，我们为每个角色启动了单独的进程。

```bash
# 初始化数据库
python main.py -init
# 首次初始化完成后，会创建admin/admin123的管理员账号
# 可以通过修改.env定义初始化账号/密码
```

```bash
# 使用单独的窗口，启动独立进程
# 启动前记得激活venv环境

# 主服务（Web、API）
python main.py
# 指挥官
python main.py -role _captain
# 安全管理员（经理）
python main.py -role _manager
# 安全工程师（操作员）
python main.py -role _operator
# 执行器
python main.py -role _executor
# 安全专家
python main.py -role _expert
```

## 📚 使用示例

### Web界面创建安全事件

登录`http://127.0.0.1:5007/`,创建安全事件。

![](app/static/images/deepsoc-home.jpg)

### 查看多Agent运行状态

![](app/static/images/deepsoc-warroom.jpg)

### 查看消息原始数据结构

![](app/static/images/deepsoc-warroom-message-structure.jpg)


### 3. curl创建安全事件

```bash
curl -X POST http://127.0.0.1:5007/api/event/create \
  -H "Content-Type: application/json" \
  -d '{
    "message": "SIEM告警外部IP 66.240.205.34正在对邮件网关服务器进行暴力破解攻击", 
    "context": "邮件网关服务器的内网IP地址192.168.22.251", 
    "severity": "medium",
    "source": "SIEM"
  }'
```

## 🤝 参与贡献

我们欢迎任何形式的贡献！

1. Fork 本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📜 相关项目

- [DeepSec](https://deepsec.top) - 中文网络安全运营领域开源语料库
- [OctoMation](https://github.com/flagify-com/OctoMation) - 社区免费版编排自动化产品

## 🌟 加入社区

- 微信社区：扫码加入（备注：deepsoc）
- 技术讨论：每周直播分享
- 项目动态：实时更新



DeepSOC群助手微信二维码

<img src="app/static/images/deepsoc-wechat-assistant.jpg" width="100" alt="DeepSOC群助手微信二维码">

## 📄 开源协议

本项目采用 [MIT](LICENSE) 协议开源。

---

<p align="center">用AI重新定义安全运营 | Redefining Security Operations with AI</p>
