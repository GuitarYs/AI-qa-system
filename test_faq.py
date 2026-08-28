# -*- coding: utf-8 -*-
"""验收测试：批量向 AI 客服发送 FAQ 清单问题，生成验收报告。"""
import json
import sys
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
OUT = "FAQ验收测试报告.md"


def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:  # 超时等
        return 0, str(e)


# (编号, 分类, 问题, 期望意图, 判定关键词)
CASES = [
    (1, "FAQ-产品套餐", "三个套餐分别多少钱？有折扣吗？", "consult", ["39", "89", "199"]),
    (2, "FAQ-产品套餐", "基础版和专业版最大的功能差别是什么？", "consult", ["版本历史", "100", "2"]),
    (3, "FAQ-产品套餐", "所有套餐都有 AI 助手吗？额度分别是多少？", "consult", ["50", "500"]),
    (4, "FAQ-产品套餐", "可以按季付费吗？", "consult", ["不支持", "按月"]),
    (5, "FAQ-产品套餐", "免费试用要钱吗？能用多久？", "consult", ["14", "试用"]),
    (6, "FAQ-产品套餐", "单个文件的大小限制是多少？", "consult", ["100", "2", "10"]),
    (7, "FAQ-发票与报销", "怎么申请开发票？在哪里操作？", "consult", ["账单与发票", "申请发票"]),
    (8, "FAQ-发票与报销", "能开增值税专用发票吗？需要什么材料？", "consult", ["营业执照", "一般纳税人"]),
    (9, "FAQ-发票与报销", "发票抬头写错了能改吗？", "consult", ["作废", "重开"]),
    (10, "FAQ-发票与报销", "个人用户能开企业抬头的发票吗？", "consult", ["授权", "企业抬头"]),
    (11, "FAQ-发票与报销", "去年的消费现在还能补开发票吗？", "consult", ["3 月 31", "补开"]),
    (12, "FAQ-发票与报销", "报销需要哪些凭证？", "consult", ["发票", "支付凭证", "明细"]),
    (13, "FAQ-账号安全", "忘记密码怎么办？", "consult", ["忘记密码", "重置"]),
    (14, "FAQ-账号安全", "怎么开启双因素认证（2FA）？", "consult", ["双因素", "身份验证器"]),
    (15, "FAQ-账号安全", "账号被锁定了怎么办？多久解锁？", "consult", ["5", "30", "解锁"]),
    (16, "FAQ-账号安全", "账号被盗 / 异常登录怎么处理？", "consult", ["退出", "冻结", "2FA"]),
    (17, "FAQ-账号安全", "一个邮箱能注册多个账号吗？", "consult", ["不能", "一个"]),
    (18, "FAQ-账号安全", "开启 2FA 后换手机了怎么办？", "consult", ["备份", "恢复码"]),
    (19, "FAQ-常见故障", "登录提示账号或密码错误，但密码是对的，怎么办？", "consult", ["Caps", "重置"]),
    (20, "FAQ-常见故障", "付了款但订单状态还是未支付？", "consult", ["回调", "重复支付"]),
    (21, "FAQ-常见故障", "同事改了文件，我这边看不到更新？", "consult", ["刷新", "同步", "权限"]),
    (22, "FAQ-常见故障", "文件上传失败提示网络错误？", "consult", ["超限", "特殊字符"]),
    (23, "FAQ-常见故障", "文件删了能找回吗？", "consult", ["回收站", "恢复"]),
    (24, "FAQ-常见故障", "网页打开很卡 / 文件编辑有延迟？", "consult", ["拆分", "浏览器"]),
    # 转人工 / 订单 / 低置信
    (25, "转人工-主动", "我要人工客服", "transfer", []),
    (26, "转人工-低置信", "你们公司 CEO 是谁？", "lowconf", []),
    (27, "订单查询", "查一下我的订单", "order", []),
    (28, "订单查询", "我的订单 CW20260715001 现在什么状态？", "order", ["CW20260715001"]),
]

USER_ID = 1  # 张三

results = []


def judge(cat, expected, r):
    """粗略判定通过与否。"""
    if expected == "consult":
        ok_intent = r.get("intent") == "consult"
        ok_src = len(r.get("sources") or []) > 0
        ok_conf = (r.get("confidence") or 0) >= 0.6
        return ok_intent and ok_src and ok_conf
    if expected == "transfer":
        return bool(r.get("transferred")) or r.get("intent") == "transfer"
    if expected == "lowconf":
        return bool(r.get("low_confidence")) or bool(r.get("transferred"))
    if expected == "order":
        return r.get("intent") == "order"
    return False


lines = []
lines.append("# AI 客服系统 · FAQ 验收测试报告\n")
lines.append("> 自动生成，逐条向 AI 客服发送问题并记录实际返回。\n")

pass_cnt = 0
total = len(CASES) + 1  # 多轮算 1 条

for idx, (num, cat, q, exp, kws) in enumerate(CASES, 1):
    st, r = post("/api/chat", {"message": q, "user_id": USER_ID, "conversation_id": None})
    ok = False
    if st == 200 and isinstance(r, dict):
        intent = r.get("intent")
        conf = r.get("confidence") or 0
        low = r.get("low_confidence")
        trans = r.get("transferred")
        ns = len(r.get("sources") or [])
        reply = (r.get("reply") or "").replace("\n", " ")
        ticket = r.get("ticket_id")
        ok = judge(cat, exp, r)
        # 关键词命中（内容正确性参考）
        kw_hit = " / ".join(k for k in kws if k in reply) if kws else "-"
        if ok:
            pass_cnt += 1
        status = "✅ PASS" if ok else "❌ FAIL"
        line = (f"| {num} | {cat} | {status} | intent={intent} conf={conf:.3f} "
                f"low={low} trans={trans} src={ns} ticket={ticket} | {kw_hit} |")
        lines.append(line)
        print(f"[{idx}/{total}] {status} intent={intent} conf={conf:.3f} src={ns} | {cat} | {q[:20]}")
        sys.stdout.flush()
    else:
        ok = False
        lines.append(f"| {num} | {cat} | ❌ FAIL | HTTP {st} | - |")
        print(f"[{idx}/{total}] FAIL HTTP {st} | {q[:20]}")
        sys.stdout.flush()
    time.sleep(0.6)

# 多轮上下文（第 29 条）
print(f"[29/{total}] 多轮上下文测试中…")
st1, r1 = post("/api/chat", {"message": "基础版多少钱？", "user_id": USER_ID, "conversation_id": None})
conv = r1.get("conversation_id") if isinstance(r1, dict) else None
time.sleep(0.6)
st2, r2 = post("/api/chat", {"message": "那专业版呢？", "user_id": USER_ID, "conversation_id": conv})
ok_multi = False
if st2 == 200 and isinstance(r2, dict):
    reply2 = (r2.get("reply") or "").replace("\n", " ")
    conf2 = r2.get("confidence") or 0
    ns2 = len(r2.get("sources") or [])
    ok_multi = conf2 >= 0.6 and ("89" in reply2 or "专业" in reply2)
    if ok_multi:
        pass_cnt += 1
    status = "✅ PASS" if ok_multi else "❌ FAIL"
    lines.append(f"| 29 | 多轮上下文 | {status} | conf={conf2:.3f} src={ns2} | 专业版价格是否被正确理解: {'89' in reply2} |")
    print(f"[29/{total}] {status} conf={conf2:.3f} src={ns2}")
else:
    lines.append(f"| 29 | 多轮上下文 | ❌ FAIL | HTTP {st2} | - |")
    print(f"[29/{total}] FAIL HTTP {st2}")

# 汇总
lines.insert(1, f"\n**结果：{pass_cnt} / {total} 条通过**\n")
lines.insert(2, "\n| # | 分类 | 结果 | 实际返回（intent/conf/low/trans/src/ticket） | 关键词命中 |\n|---|---|---|---|---|\n")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n===== 测试完成：{pass_cnt}/{total} 通过，报告已写入 {OUT} =====")
