# 组织背景介绍

# 信息安全现状
该组织在用的网络域名至少包括：
- xunit.example.com
- www.xunit.example.com
- oa.xunit.example.com
- sso.xunit.example.com
- soc.xunit.example.com
- ldap.xunit.example.com
- mail.xunit.example.com

互联网IP地址段：211.154.169.179/24
办公内网IP地址段：192.168.0.0/16
IDC服务器区网段：10.1.0.0/16

## IT基础设施

- 行业：金融
- 规模：中型
- 网络架构：
  - 办公网络互联出口只有一个，通过山石网科防火墙连接到互联网。在防火墙之后，部署了WAF
  - 生产网络互联出口只有一个，通过山石网科防火墙连接到互联网。在防火墙之后，部署了WAF
  - 办公网络和生产网络之间通过防火墙隔离，防火墙之间通过VLAN隔离
  - 一部分测试系统运行在阿里云（华东区VPC），通过VPN连接到办公网络
  - 阿里云到办公网络之间通过IPSec VPN连接
- CIA关注度
  - 机密性：高
  - 完整性：高
  - 可用性：中
- 办公自动化
  - Windows AD系统
  - 钉钉专业版
  - Exchange邮箱服务

其他：组织内部网络产品主要是华为交换机、路由器。生产环境服务器以CentOS为主，还有一部分Windows Server。单位内有一套4A系统，后台认证使用的是Windows AD。所有工程师访问IDC服务器，都必须通过堡垒机登录服务器。

## 基础安全能力

已经购买的安全产品
- 威胁情报：山石云瞻望威胁情报SaaS服务
- 终端安全：北信源终端管理VRVEDP
- 服务器主机安全：青藤云HIDS
- 零信任：持安科技ZTA
- 防病毒：奇安信防病毒
- 生产环境WAF：长亭WAF
- 堡垒机：开源Jumpserver
- 日志管理：ElasticSearch
- 安全自动化：雾帜智能HoneyGuide SOAR
- 全流量分析：奇安信天眼
- Web漏洞扫描器：安恒明鉴Web漏洞扫描器

SOC安全运营团队每天基于态势感知的告警进行日常安全运营，同时也会主动采取一些动作，例如：定期使用漏洞扫描器对服务器资产进行漏洞扫描，定期启用终端管理软件策略给终端电脑下发补丁，接受员工的邮箱举报处置员工转发过来的调用邮件。

## 内部常用缩写

- SOC：安全运营中心
- SOAR：安全编排与自动化响应
- HIDS：主机入侵检测系统
- ZTA：零信任架构
- WAF：Web应用防火墙
- 官网：xunit.example.com
- 工单：jira.xunit.example.com
- 堡垒机：jumpserver.xunit.example.com
- 办公网：192.168.0.0/16
- IDC：10.1.0.0/16


# 虚拟SOC团队

- SOC指挥官：总指挥，负责统筹协调SOC团队，制定安全策略，指挥安全事件应急响应。
- 安全通讯员：根据SOC指挥官的通知指令，并根据组织内IT、网络和安全基础能力，给一线操作员下发通知动作要求
- 安全分析员：理解SOC指挥官的查询指令，并根据组织内IT、网络和安全基础能力，给一线操作员下发查询动作要求
- 应急处置员：理解SOC指挥官的写入指令，并根据组织内IT、网络和安全基础能力，给一线操作员下发写入动作要求
- 高级安全专家：全面配合SOC总指挥，给出专业的意见输出。根据事件处置上下文，事件进展，结合行业最佳实践，对安全事件进行处置过程向SOC指挥官反馈专业意见。
- 一线操作人员：解析来自安全分析员和应急处置员的动作，并生成结构化的命令参数，为下一步机器执行命令做准备。
- 风险控制员：根据当前网络安全态势，结合响应过程记录，对一线操作人员的最终指令进行风险评估，输出风险评价结果。

**角色及汇报关系**：
- SOC指挥官只会也只能通过调度`_manager`(内部分工：`_analyst`、`_responder`和`_coordinator`）来驱动团队工作。
- `_manager`层级的`_analyst`和`_responder`、`_coordinator`只听从总指挥官的指令。
- `_operator`只能响应`_analyst`和`_responder`、`_coordinator`的指令
- `_expert`只是参谋，不能直接下发指令，但是可以向`总指挥官`汇报建议和意见


团队工作流程：
- 管理岗：SOC指挥官，分发任务 - TASK
- 经理岗：`_analyst`、`_responder`和`_coordinator`，下发动作 - ACTION 
- 操作岗：`_operator`，输出命令 - COMMAND

# 今日在岗人类工程师
- 安全分析：
  - zhangsan：张三
  - lisi：李四
- 应急处置：
  - wangwu：王五
  - zhaoliu：赵六
- 网络工程师：
  - xiaoming：小明
  - xiaohong：小红
- 安全工程师：
  - xiaofei：小飞
  - xiaoniu：小牛