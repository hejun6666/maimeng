# Amazon Listing 自动文案 Skill 使用说明

这份文档给运营同事使用。你不需要懂代码，只要照着下面的话术在 Codex 里输入即可。

## 这个 Skill 是干什么的

`amazon-listing-auto-copywriter` 用来生成 Amazon US / CA / UK / DE 站点的商品 Listing 文案。

它会先自动抓取 Amazon 前台公开竞品信息，再输出：

- 可复制到 Amazon 的标题、五点、描述、后台搜索词
- 对应主文案的一对一中文翻译
- 给运营复核的竞品依据、关键词池、待核实清单、合规风险提醒

注意：它不使用卖家精灵、SIF、ABA 等付费数据接口，只用 Amazon 前台公开信息。

它的竞品搜索逻辑是：Codex 先根据产品和站点生成当地买家会搜的关键词、相关性词、目标 BSR 类目；脚本只负责抓取 Amazon 页面、抽取公开字段、按 BSR 和近月购买热度等信号排序。脚本不会自己从一个中文品名里猜市场。

## 第一次安装

在 Codex 里输入：

```text
帮我安装这个 skill：https://github.com/hejun6666/maimeng/tree/main/skills/amazon-listing-auto-copywriter
```

安装完成后，重启 Codex。

## 怎么调用

最简单的话术：

```text
用 amazon-listing-auto-copywriter，产品是荧光笔
```

如果要指定站点：

```text
用 amazon-listing-auto-copywriter，产品是荧光笔，美国站
```

```text
用 amazon-listing-auto-copywriter，产品是婴儿围栏，加拿大站
```

```text
用 amazon-listing-auto-copywriter，产品是儿童显微镜，英国站
```

```text
用 amazon-listing-auto-copywriter，产品是荧光笔，德国站
```

如果你有产品资料，建议这样写：

```text
用 amazon-listing-auto-copywriter，产品是荧光笔，美国站。
已知信息：
- 8支装
- 多色
- 斜头
- 适合学生、教师、办公室、手账
- 不确定是否速干、不确定是否无毒
```

## 建议提供哪些产品信息

信息越多，文案越准。能提供多少就提供多少：

```text
产品名：
站点：美国站 / 加拿大站 / 英国站 / 德国站
数量：
颜色：
尺寸：
材质：
核心功能：
适用人群：
使用场景：
包装内包含什么：
确认可以写的认证或测试：
不能确定、不要乱写的信息：
```

示例：

```text
用 amazon-listing-auto-copywriter，产品是儿童显微镜，美国站。
已知信息：
- 适合儿童科学启蒙
- 配收纳盒
- 有LED灯
- 倍率不确定
- 是否适合具体年龄段不确定
- 不要写STEM认证
```

## 输出结果怎么看

默认输出分三块。

### 1. Amazon Copy - Enhanced Candidate Version

这是主文案区，可给运营复制修改。

包括：

- Product Title
- 5 Bullet Points
- Product Description
- Backend Search Terms

美国站、加拿大站、英国站会输出英文；德国站会输出德文。主文案区不会混中文，也不会出现 `[待核实]`。

### 2. 中文文案对照

这是给运营看的中文翻译。

要求是一对一翻译主文案内容：

- 主文案标题对应中文标题
- 主文案五点逐条对应中文五点
- 主文案描述完整翻译
- 后台搜索词翻译成中文含义

这部分不是给 Amazon 复制的。

### 3. 中文运营复核区

这是运营必须看的地方。

重点看：

- 竞品抓取依据：用了哪些 ASIN，销量热度、BSR、评分、评论、图片数如何
- 查询词依据：Codex 为这个站点生成了哪些当地买家搜索词
- 竞品洞察：竞品都在怎么写
- 关键词池：哪些词值得参考
- 待核实清单：哪些功能、尺寸、材质、认证不能直接相信
- 合规风险：哪些词不能乱写

## 运营复核重点

生成结果不是直接无脑上架。运营至少要核对：

- 尺寸是否真实
- 数量是否真实
- 颜色是否真实
- 材质是否真实
- 是否真的包含配件
- 是否真的速干、防水、无毒、可水洗
- 是否真的有认证
- 年龄段是否能写
- 是否涉及医疗、安全、儿童合规风险

如果不能确认，就删掉或改弱。

## 常用提示词模板

### 只有产品名

```text
用 amazon-listing-auto-copywriter，产品是【产品名】，美国站
```

### 有基础参数

```text
用 amazon-listing-auto-copywriter，产品是【产品名】，美国站。
已知信息：
- 【参数1】
- 【参数2】
- 【参数3】
不确定信息：
- 【不确定1】
- 【不确定2】
```

### 想让文案更像美国本土 Listing

```text
用 amazon-listing-auto-copywriter，产品是【产品名】，美国站。
请按美国本土 Amazon Listing 语感写，五点要有场景、痛点、功能支撑和结果感。
中文对照要逐句完整翻译。
```

### 想做英国站

```text
用 amazon-listing-auto-copywriter，产品是【产品名】，英国站。
请按英国 Amazon Listing 语感写，允许使用自然的英式表达。
中文对照要逐句完整翻译。
```

### 想做德国站

```text
用 amazon-listing-auto-copywriter，产品是【产品名】，德国站。
主文案用德语写。中文对照要逐句完整翻译。
```

### 想限制不要乱写

```text
用 amazon-listing-auto-copywriter，产品是【产品名】，美国站。
以下内容没有资料支持，不要写进英文主文案：
- non-toxic
- waterproof
- certified
- safe for kids
- BPA-free
```

## 怎么判断 Skill 成功触发

如果成功触发，输出里通常会有：

```text
Amazon Copy - Enhanced Candidate Version
中文文案对照
中文运营复核区
```

并且会看到竞品抓取依据表，里面有：

```text
ASIN
Bought Past Month
Best Sellers Rank
Rating
Reviews
Images
```

如果 Codex 只随便写了一段文案，没有竞品依据，说明没有正确触发或没有按流程跑。

## 常见问题

### 安装后为什么调用不出来

先重启 Codex。

如果还是不行，确认安装地址是否是：

```text
https://github.com/hejun6666/maimeng/tree/main/skills/amazon-listing-auto-copywriter
```

### 为什么有些卖点放在待核实清单

因为竞品写了不代表我们的产品也有。比如 `quick-dry`、`non-toxic`、`waterproof`、`certified`、`BPA-free` 都必须有资料支持。

### 能不能直接复制英文上架

建议运营复核后再上架。英文主文案是“强转化候选稿”，不是免审核终稿。

### 支持哪些站点

默认支持：

- Amazon US
- Amazon CA
- Amazon UK
- Amazon DE

不写站点时，默认美国站。
