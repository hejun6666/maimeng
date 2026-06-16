# 迈萌 Codex Skills


## Skills

### Amazon Listing 自动文案

安装地址：

```text
https://github.com/hejun6666/maimeng/tree/main/skills/amazon-listing-auto-copywriter
```

用途：根据产品基础信息和公开竞品数据，生成 Amazon US / CA / UK / DE 可复制 Listing 文案、中文对照和运营复核清单。

### Amazon AI Shopping Listing 文案

安装地址：

```text
https://github.com/hejun6666/maimeng/tree/main/skills/amazon-ai-shopping-listing-copywriter
```

用途：保留原 Amazon Listing 文案能力，同时增加 AI Shopping / Rufus / Alexa for Shopping / GEO 友好结构，让文案更容易被 AI 购物助手理解、匹配和引用。它不保证排名、推荐或收录。

### Browser Use 网页自动填表

安装地址：

```text
https://github.com/hejun6666/maimeng/tree/main/skills/browser-use-form-fill
```

用途：给不懂命令行的公司同事使用，让 Codex 借助开源 `browser-use` CLI 打开可见浏览器，把用户提供的数据填到网站、政务/财税平台、CRM、后台系统等网页表单里，填完停住给人工检查。内置环境检查脚本，会检测 `browser-use`、`uvx`、Chrome、Edge 或 Chromium。

### 领星 SKU 补货下单助手

安装地址：

```text
https://github.com/hejun6666/maimeng/tree/main/skills/lingxing-replenishment-planner
```

用途：通过 browser-use 打开或接管用户自己的 Chrome 领星 ERP 网页，读取销售 > Listing 当前筛选结果，批量获取 SKU 销量，再匹配 FBA/AWD 库存，生成补货建议、每周补货参考量和工厂下单建议。

### 1688 源头厂家筛选询价助手

安装地址：

```text
https://github.com/hejun6666/maimeng/tree/main/skills/1688-source-factory-finder
```

用途：通过开源 Browser Use 项目的 `browser-use` 命令控制用户已登录的 1688 网页端，按图片、关键词、商品链接或当前页面找候选供应商，默认询问 7-9 家；先发商品卡片/链接再发默认询价话术，按真人采购节奏逐家发送、回收回复、追问缺字段，并导出公司采购跟进 Excel。这里的 `browser-use` 不是 Codex 内置 Browser 插件。

### 选品漏斗产品数据补齐助手

安装地址：

```text
https://github.com/hejun6666/maimeng/tree/main/skills/product-profit-data-filler
```

用途：面向飞书多维表格选品/利润测算表。同事在 Codex 输入框里提供飞书多维表格链接、Feishu App ID 和 App Secret 后，Codex 通过 Feishu OpenAPI 读取产品图和缺失字段，按图片去 1688 找高相似商品，抓采购价、包装尺寸、重量和产品属性；Amazon 固定英国站 `amazon.co.uk`，取相似竞品售价里的中位价；1688 人民币采购价按固定汇率 9.17 换算为 GBP 后写回表格。

## 使用文档

- [Amazon Listing 自动文案 Skill 使用说明](docs/amazon-listing-skill-usage.md)
- [领星 SKU 补货下单助手使用说明](docs/lingxing-replenishment-skill-usage.md)
- [1688 源头厂家筛选询价助手使用说明](docs/1688-source-factory-skill-usage.md)

如需 Word 版手册，用 Codex 单独生成并发送，不纳入 git。

## 安装后

安装 skill 后需要重启 Codex，重启后再用 skill 名称调用。
