// 仅供乐呵小报 · 案例数据（阶段1 mock，阶段3 由自动化写入并替换为 JSON + fetch）
// 字段：date 日期 / source 资料来源 / sourceUrl 来源链接 / advertiser 广告主 / agency 代理商
//       campaignType campaign 类型 / title 标题 / summary 简单阐释 / images 2-3 张精选图（可选，留空显示占位）
window.CASES = [
  {
    id: "demo-001",
    date: "2026-10-14",
    source: "数英网",
    sourceUrl: "https://www.digitaling.com/",
    advertiser: "三顿半",
    agency: "（示例）某创意热店",
    campaignType: "品牌Campaign",
    title: "返航计划：把咖啡空罐变成下一次出发",
    summary:
      "以「返航」为隐喻，把回收空罐做成线下快闪与社群仪式，把环保动作包装成品牌浪漫，强社交传播。",
    images: [],
  },
  {
    id: "demo-002",
    date: "2026-10-11",
    source: "广告门",
    sourceUrl: "https://www.adquan.com/",
    advertiser: "美团",
    agency: "（示例）内部团队",
    campaignType: "节点营销",
    title: "中秋「团圆」反向叙事：一个人也要好好吃饭",
    summary:
      "避开阖家团圆套路，对准独居青年，用「一个人」的细腻场景做情绪共鸣，切口小而准。",
    images: [],
  },
  {
    id: "demo-003",
    date: "2026-10-08",
    source: "SocialBeta",
    sourceUrl: "https://socialbeta.com/",
    advertiser: "观夏",
    agency: "（示例）品牌自运营",
    campaignType: "新品上市",
    title: "把「东方香」做成可收藏的器物叙事",
    summary:
      "用东方植物与城市记忆做内容资产，产品即内容，强调材质与气味的故事感，适合种草型打法参考。",
    images: [],
  },
  {
    id: "demo-004",
    date: "2026-10-05",
    source: "梅花网",
    sourceUrl: "https://www.meihua.info/",
    advertiser: "大窑汽水",
    agency: "（示例）省广集团",
    campaignType: "渠道下沉",
    title: "大瓶快乐：用「聚餐场景」撬动下沉市场",
    summary:
      "以家庭聚餐、夜市大排档等强场景绑定大包装，价格锚点清晰，适合参考下沉渠道的媒介与话术组合。",
    images: [],
  },
];
