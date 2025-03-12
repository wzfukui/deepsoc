```yaml
### SOAR 安全剧本能力清单
playbooks:
  - id: 12321435630187042
    name: query_asset_info_by_ip
    desc: 根据IP地址查询资产信息
    logic: 根据给定的IP地址，查询资产信息，包括：IP地址、资产类型、资产所属部门、资产所属业务线、资产所属负责人、资产所属负责人联系方式等。
    params:
      - name: dst
        desc: 待查询的IP地址
        required: true

  - id: 12302548181076017
    name: freeze_windows_ad_user
    desc: 冻结Windows AD用户
    logic: 根据给定的用户名，冻结Windows AD用户
    params:
      - name: user_name
        desc: 待冻结的Windows AD用户名
        required: true
      - name: freeze_duration_minute
        desc: 冻结时长(分钟)
        default: 60
        required: false

  - id: 12321431702878375
    name: unblock_ip_by_firewall_internet
    desc: 防火墙解封IP(互联网)
    logic: 根据给定的IP地址，解封防火墙的访问
    params:
      - name: src
        desc: 待解封的IP地址
        required: true

  - id: 12321426001638099
    name: block_ip_by_firewall_internet
    desc: 防火墙阻断IP(互联网)
    logic: 根据给定的IP地址，阻断防火墙的访问
    params:
      - name: src
        desc: 待阻断的IP地址
        required: true
      - name: block_duration_minute
        desc: 阻断时长(分钟)
        default: 60
        required: false

  - id: 12321418519526014
    name: Send_Message_To_Dingtalk
    desc: 发送消息到钉钉
    logic: 发送消息到钉钉，可以返回：成功或者失败信息。
    params:
      - name: message
        desc: 消息内容
        required: true
      - name: group_id
        desc: 钉钉群组ID
        required: false

  - id: 12321406690537761
    name: General_IP_Location_Query
    desc: 通用IP地址位置查询(支持IPv4和IPv6)
    logic: 根据给定的IP地址，查询位置信息，可以返回：IP地址、位置信息、位置来源、位置描述等。
    params:
      - name: src
        desc: 待查询的IP地址
        required: true

  - id: 12316887511154270
    name: General_IP_Threat_Intelligence_Query
    desc: 通用IP地址威胁情报信息查询
    logic: 根据给定的IP地址，查询（可能多源）威胁情报信息，可以返回：IP地址、威胁情报类型、威胁情报来源、威胁情报描述等。
    params:
      - name: src
        desc: 待查询的IP地址
        required: true

  - id: 12302548181076023
    name: Anti_Phising_Email
    desc: 钓鱼邮件应急处置
    logic: 针对钓鱼邮件启动调查分析和处置，涉及到威胁情报、沙箱、邮件通知、账号操作等等
    params:
      - name: eml_file_path
        desc: 钓鱼邮件eml文件路径
        example: /tmp/202409160909.eml
        required: true

  - id: 12302548181076024
    name: Brute_Force_Login_Cloud  
    desc: 云平台上的暴力破解登录事件
    logic: 快速阻止云平台上的暴力破解攻击行为，调查攻击影响
    params:
      - name: src
        desc: 攻击者IP地址
        required: true
      - name: dst
        desc: 被攻击者IP地址
        required: false

  - id: 12302548181076025
    name: Web_SQL_Injection
    desc: Web攻击事件-SQL注入
    logic: 拦截SQL注入攻击，开展安全漏洞自检
    params:
      - name: src
        desc: 攻击者IP地址
        required: true
      - name: dstdomain
        desc: 被攻击的域名或站点
        required: false
      - name: payload
        desc: 攻击载荷
        required: true

  - id: 12302548181076026
    name: github_info_leak_investigation
    desc: github信息泄露应急调查
    logic: 针对github信息泄露事件，克隆项目，留取证据，根据项目深度挖掘
    params:
      - name: url
        desc: github泄露的url地址
        example: https://github.com/orgs/org_name/repositories
        required: true
      - name: dig_deepth
        desc: 挖掘深度
        default: 1
        required: false

  - id: 12302548181076027
    name: endpoint_pc_compromise_investigation
    desc: 终端主机被入侵应急调查
    logic: 针对终端主机被入侵事件，开展应急调查，先完成终端主机的隔离，然后开展攻击日志的分析，涉及到准入系统、EDR、防火墙等
    params:
      - name: host_ip
        desc: 被入侵的主机IP地址
        required: true
      - name: host_mac
        desc: 被入侵的主机MAC地址
        required: false
      - name: attack_type
        desc: 攻击类型
        example: 钓鱼、勒索软件、木马病毒
        required: false

  - id: 12302548181076028
    name: employee_email_compromise_investigation
    desc: 员工邮箱被入侵应急调查
    logic: 针对员工邮箱被入侵事件，先完成邮箱的禁用，然后开展攻击日志的分析，定位攻击者可能尝试攻击其他邮箱账号，一起通告。涉及到邮箱系统、AD域控、防火墙、SMTP等等
    params:
      - name: email
        desc: 被入侵的邮箱地址
        required: true

  - id: 12321445036046216
    name: os_login_log_query
    desc: 操作系统登录日志查询
    logic: 根据给定的操作系统IP地址，查询最近登录日志
    params:
      - name: src
        desc: 操作系统IP地址
        required: true
      - name: time_window_minute
        desc: 时间窗口(分钟)
        default: 60
        required: false

  - id: 12302548181076030
    name: email_login_log_query
    desc: 邮箱登录日志查询
    logic: 根据给定的邮箱IP地址，查询最近登录日志
    params:
      - name: email
        desc: 邮箱地址
        required: true
      - name: time_window_minute
        desc: 时间窗口(分钟)
        default: 60
        required: false
```