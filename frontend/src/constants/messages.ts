export const MESSAGES = {
  product: 'lakePack',
  productCn: '数据湖小文件合并与分区整理工坊',
  customer: '拾光内容平台 · 离线数仓小队',
  background: 'S3 兼容对象存储 40TB · Parquet 表 60 张 · Flink 每小时落小文件',
  strategyNote:
    'FFD：单分区内低于阈值的文件按大小降序 first-fit-decreasing 装进目标大小；仅重写多文件箱，单文件箱保持原样。',
  readonlyNotice: '当前为只读角色（analyst）：可以查看分区健康度、计划与快照 diff，但不能生成或执行合并计划。',
}
