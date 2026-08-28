# AI 客服系统 · FAQ 验收测试报告


**结果：29 / 29 条通过**


| # | 分类 | 结果 | 实际返回（intent/conf/low/trans/src/ticket） | 关键词命中 |
|---|---|---|---|---|

> 自动生成，逐条向 AI 客服发送问题并记录实际返回。

| 1 | FAQ-产品套餐 | ✅ PASS | intent=consult conf=0.789 low=False trans=False src=4 ticket=None | 39 / 89 / 199 |
| 2 | FAQ-产品套餐 | ✅ PASS | intent=consult conf=0.864 low=False trans=False src=4 ticket=None | 版本历史 / 100 / 2 |
| 3 | FAQ-产品套餐 | ✅ PASS | intent=consult conf=0.894 low=False trans=False src=4 ticket=None | 50 / 500 |
| 4 | FAQ-产品套餐 | ✅ PASS | intent=consult conf=0.898 low=False trans=False src=4 ticket=None | 不支持 / 按月 |
| 5 | FAQ-产品套餐 | ✅ PASS | intent=consult conf=0.820 low=False trans=False src=4 ticket=None | 14 / 试用 |
| 6 | FAQ-产品套餐 | ✅ PASS | intent=consult conf=0.886 low=False trans=False src=4 ticket=None | 100 / 2 / 10 |
| 7 | FAQ-发票与报销 | ✅ PASS | intent=consult conf=0.839 low=False trans=False src=4 ticket=None | 账单与发票 / 申请发票 |
| 8 | FAQ-发票与报销 | ✅ PASS | intent=consult conf=0.802 low=False trans=False src=4 ticket=None | 营业执照 / 一般纳税人 |
| 9 | FAQ-发票与报销 | ✅ PASS | intent=consult conf=0.841 low=False trans=False src=4 ticket=None | 作废 / 重开 |
| 10 | FAQ-发票与报销 | ✅ PASS | intent=consult conf=0.918 low=False trans=False src=4 ticket=None | 授权 / 企业抬头 |
| 11 | FAQ-发票与报销 | ✅ PASS | intent=consult conf=0.896 low=False trans=False src=4 ticket=None | 补开 |
| 12 | FAQ-发票与报销 | ✅ PASS | intent=consult conf=0.833 low=False trans=False src=4 ticket=None | 发票 / 支付凭证 / 明细 |
| 13 | FAQ-账号安全 | ✅ PASS | intent=consult conf=0.806 low=False trans=False src=4 ticket=None | 忘记密码 / 重置 |
| 14 | FAQ-账号安全 | ✅ PASS | intent=consult conf=0.893 low=False trans=False src=4 ticket=None | 双因素 / 身份验证器 |
| 15 | FAQ-账号安全 | ✅ PASS | intent=consult conf=0.864 low=False trans=False src=4 ticket=None | 5 / 30 / 解锁 |
| 16 | FAQ-账号安全 | ✅ PASS | intent=consult conf=0.869 low=False trans=False src=4 ticket=None | 退出 / 冻结 / 2FA |
| 17 | FAQ-账号安全 | ✅ PASS | intent=consult conf=0.918 low=False trans=False src=4 ticket=None | 不能 / 一个 |
| 18 | FAQ-账号安全 | ✅ PASS | intent=consult conf=0.933 low=False trans=False src=4 ticket=None | 备份 / 恢复码 |
| 19 | FAQ-常见故障 | ✅ PASS | intent=consult conf=0.860 low=False trans=False src=4 ticket=None | Caps / 重置 |
| 20 | FAQ-常见故障 | ✅ PASS | intent=consult conf=0.882 low=False trans=False src=4 ticket=None | 回调 / 重复支付 |
| 21 | FAQ-常见故障 | ✅ PASS | intent=consult conf=0.889 low=False trans=False src=4 ticket=None | 刷新 / 同步 / 权限 |
| 22 | FAQ-常见故障 | ✅ PASS | intent=consult conf=0.874 low=False trans=False src=4 ticket=None | 超限 / 特殊字符 |
| 23 | FAQ-常见故障 | ✅ PASS | intent=consult conf=0.849 low=False trans=False src=4 ticket=None | 回收站 / 恢复 |
| 24 | FAQ-常见故障 | ✅ PASS | intent=consult conf=0.889 low=False trans=False src=4 ticket=None | 拆分 / 浏览器 |
| 25 | 转人工-主动 | ✅ PASS | intent=transfer conf=0.000 low=True trans=True src=0 ticket=15 | - |
| 26 | 转人工-低置信 | ✅ PASS | intent=consult conf=0.434 low=True trans=True src=4 ticket=16 | - |
| 27 | 订单查询 | ✅ PASS | intent=order conf=1.000 low=False trans=False src=0 ticket=None | - |
| 28 | 订单查询 | ✅ PASS | intent=order conf=1.000 low=False trans=False src=0 ticket=None | CW20260715001 |
| 29 | 多轮上下文 | ✅ PASS | conf=0.727 src=4 | 专业版价格是否被正确理解: True |