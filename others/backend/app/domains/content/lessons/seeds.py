"""Six original draft lessons. Bind only actual inserted SceneAsset UUIDs, never fake versions."""
from html import escape
from uuid import UUID

from app.domains.content.lessons.scenes import validate_svg
from app.domains.content.lessons.schemas import LessonContent
from app.domains.content.questions.schemas import fingerprint
from app.domains.content.questions.seeds import TOPICS, provenance

# Coordinates are viewBox pixels; private target indexes never appear in asset markup.
ZONES = ((80, 145, 350, 145), (530, 145, 350, 145), (80, 355, 350, 145), (530, 355, 350, 145))
SPECS = {
    "entry": {
        "labels": ("防护用品领取台", "实验台上的饮料瓶", "洗手与整理区", "应急通行区域"), "target": 1,
        "locate": "按本关情境，点击需要移出实验操作区的饮料瓶所在区域。",
        "short": "入室前先确认本次任务的风险、授权和防护要求。所需防护不齐时暂停，向教师核对；防护不能代替规程和工程控制。应急设施及通道要保持可达。本关饮料瓶是情境中的无关个人物品，不应留在实验操作台。",
        "choice": ("面对尚未确认的防护要求，本关的选择是什么？", "暂停并向教师核对", "按以前经验直接开工", "让同伴替自己承担风险"),
        "order": ("确认本次任务", "核对准入与防护", "获准后按规程操作", "按要求离室整理"),
    },
    "electric": {
        "labels": ("经核对的供电区", "电源线破损的仪器", "设备操作记录台", "工具存放区"), "target": 1,
        "locate": "点击情境中应暂停使用并报告的电源线破损仪器所在区域。",
        "short": "上电前核对设备要求、供电适配和外观状态。破损线缆、异常发热或保护动作需要停用报告，不能绕过保护。断开电源并不保证内部储能已经消失，拆修由受训授权人员完成。本关只练习异常识别，不要求学生维修。",
        "choice": ("设备保护频繁动作时，本关要求怎样处理？", "停止使用并报告排查", "绕过保护继续运行", "只遮挡提示灯"),
        "order": ("阅读设备要求", "核对供电与外观", "确认后按规程使用", "完成规定的结束检查"),
    },
    "emergency": {
        "labels": ("示意出口方向", "实验工作台", "应急信息板", "预案指定集合区"), "target": 3,
        "locate": "本图只是一张教学示意图，请点击预案指定集合区。",
        "short": "到岗前了解本楼报警方式、疏散路线和集合点。实际事件按现场预案与应急人员指令行动，在安全位置准确报告已知信息；未受训者不承担超出能力的处置。撤离后参加人员清点，不为取回物品擅自返场。图中位置不是校园真实疏散地图。",
        "choice": ("已撤离后怀疑有人滞留，本关建议怎样做？", "向应急人员提供已知线索", "未经授权自行返回", "把猜测发布成确定结论"),
        "order": ("演练前查阅本楼预案", "辨认路线与集合点", "参加指导下的演练", "演练后记录改进事项"),
    },
    "storage": {
        "labels": ("已标识的储存柜", "待确认的无标签容器", "安全资料查阅台", "相容性核对区"), "target": 1,
        "locate": "点击情境中不能直接选用、需要交由负责人员确认身份的容器所在区域。",
        "short": "先确认产品身份，再查阅对应安全数据表并开展任务风险评估。安全数据表提供危害、操作和储存信息，但不等于完成了本次风险评估。标签不清的物品不靠气味、颜色或记忆猜测；储存条件按相容性和本地要求核对。",
        "choice": ("两个瓶子标签不清但颜色一样，可以据此混放吗？", "不能，须先确认内容与相容性", "可以，颜色足够说明性质", "可以，只要瓶子一样大"),
        "order": ("确认产品身份", "查阅对应安全数据表", "核对相容性与储存条件", "按规定放置并更新记录"),
    },
    "ventilation": {
        "labels": ("状态报警的通风柜", "普通工作台", "规程查阅台", "设备检查记录区"), "target": 0,
        "locate": "点击情境中需要暂停相关操作并报告检查的报警设备所在区域。",
        "short": "根据实验风险选择适用的工程控制设备，使用前确认状态和操作条件。照明不代表通风正常，普通风扇不直接等同于局部排风。设备报警不靠静音解决；不同类型柜体不能仅凭名称互相替代。按设备标识和本地规程使用，不把通风柜作为废物处置设施。",
        "choice": ("发现通风柜状态不明时，本关要求什么？", "暂停并请负责人员确认", "只要灯亮就直接用", "增加风扇代替检查"),
        "order": ("确认操作的控制需求", "选择适用设备", "核对设备状态与要求", "获准后按规程操作"),
    },
    "waste": {
        "labels": ("有标识的收集容器", "未知液体泄漏区域", "交接记录台", "收集用品准备区"), "target": 1,
        "locate": "请在示意图中标记未知液体泄漏所在区域，不代表要求靠近现场。",
        "short": "操作前规划废物种类、相容性、容器、标识和指定交接路径。未知内容不凭外观合并，不以通风蒸发代替规范处理。未经训练、超出能力或情况不明的泄漏，应避免暴露、警示他人并按本地预案报告。本关不教授未知化学品的中和或清理配方。",
        "choice": ("面对未知泄漏且没有处置训练，本关要求什么？", "避免暴露并按预案报告", "凑近闻气味", "随意混入其他液体"),
        "order": ("预估本次废物类型", "确认分类与收集要求", "备妥合规标识容器", "按规定收集交接"),
    },
}


def scene_svg(topic):
    title = TOPICS[topic][1]
    labels = SPECS[topic]["labels"]
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600" role="img"><title>{escape(title)}教学场景</title>',
        '<desc>原创实验室俯视示意，四个区域均有文字；非真实校园平面图。</desc>',
        '<rect x="0" y="0" width="960" height="600" fill="#eef7f6"/>',
        '<path d="M40 105 L920 105 L920 545 L40 545 Z" fill="#ffffff" stroke="#537b8a" stroke-width="4"/>',
        f'<text x="55" y="60" font-size="28" fill="#173f55">{escape(title)} · 场景观察</text>',
        '<path d="M455 130 L455 520 M500 130 L500 520" stroke="#b5dcd8" stroke-width="3"/>']
    for i, ((x, y, width, height), label) in enumerate(zip(ZONES, labels, strict=True)):
        elements += [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="#e0efef" stroke="#759fa9" stroke-width="2"/>',
            f'<rect x="{x + 32}" y="{y + 28}" width="60" height="60" rx="8" fill="#7db7ba"/>',
            f'<circle cx="{x + 62}" cy="{y + 53}" r="13" fill="#ffffff"/>',
            f'<text x="{x + 108}" y="{y + 55}" font-size="18" fill="#173f55">区域 {i + 1}</text>',
            f'<text x="{x + 18}" y="{y + 120}" font-size="18" fill="#173f55">{escape(label)}</text>']
    # Topic-specific visible objects; no hidden score/answer attributes or external resources.
    if topic == "entry":
        elements.append('<path d="M830 190 L850 190 L855 240 L825 240 Z" fill="#4f87a0"/>')
    elif topic == "electric":
        elements.append('<path d="M825 205 L840 215 M850 220 L865 230" stroke="#386272" stroke-width="5"/>')
    elif topic == "emergency":
        elements.append('<path d="M815 390 L840 390 L840 380 L860 400 L840 420 L840 410 L815 410 Z" fill="#478c82"/>')
    elif topic == "storage":
        elements.append('<path d="M835 182 L850 182 L850 198 L860 215 L860 243 L825 243 L825 215 L835 198 Z" fill="#80b3c6"/>')
    elif topic == "ventilation":
        elements.append('<circle cx="385" cy="170" r="11" fill="#af9147"/><text x="345" y="225" font-size="16" fill="#173f55">报警</text>')
    else:
        elements.append('<ellipse cx="840" cy="235" rx="24" ry="13" fill="#84b4bb"/>')
    elements.append('<text x="55" y="579" font-size="16" fill="#406878">教学草稿 · 依本地规程与教师审核使用</text></svg>')
    return validate_svg("".join(elements))


def lesson_seed(topic: str, asset_id: UUID):
    if not isinstance(asset_id, UUID):
        raise ValueError("关卡须绑定真实插入的SceneAsset UUID")
    spec = SPECS[topic]
    title = TOPICS[topic][1]
    scene_id = "scene-" + topic
    stem, good, bad1, bad2 = spec["choice"]
    def item_id(label):
        return "v" + fingerprint({"topic": topic, "label": label})[:12]
    # Keep private correctness in scoring only, never labels or asset markup.
    activities = [{"id": "decide", "kind": "choice", "selection": "single", "prompt": stem,
        "options": [{"id": item_id(label), "label": label} for label in (good, bad1, bad2)]},
        {"id": "locate", "kind": "hotspot", "prompt": spec["locate"], "scene_id": scene_id,
         "regions": [{"id": item_id(label), "label": label, "x": x / 960, "y": y / 600, "width": width / 960, "height": height / 600}
            for i, ((x, y, width, height), label) in enumerate(zip(ZONES, spec["labels"], strict=True))]},
        {"id": "plan", "kind": "order", "prompt": "按本关教学约定整理准备/演练步骤；本题不是突发事件现场的处置指令。",
         "items": [{"id": item_id(text), "label": text} for text in spec["order"]]}]
    steps = "；".join(spec["order"])
    return LessonContent(title=title, short_lesson=spec["short"] + "\n本关教学步骤：" + steps + "。\n内容待教师审核，使用前核对本校要求。",
        scene={"id": scene_id, "svg_asset_id": asset_id,
            "accessible_description": "实验室俯视教学图，从左上、右上、左下、右下依次为：" + "、".join(spec["labels"]) + "。"},
        activities=activities, scoring=[{"activity_id": "decide", "correct_ids": [item_id(good)], "explanation": "应按本关说明核对条件，在受训授权范围内行动。"},
            {"activity_id": "locate", "correct_ids": [item_id(spec["labels"][spec["target"]])], "explanation": "请结合场景文字与本关短课识别对应区域，实际行动以现场预案为准。"},
            {"activity_id": "plan", "correct_ids": [item_id(text) for text in spec["order"]], "explanation": "本关的教学步骤为：" + steps + "。"}],
        provenance=provenance(topic))
