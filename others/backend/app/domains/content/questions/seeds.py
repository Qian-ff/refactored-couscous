"""Original AI-assisted teaching drafts. No approval, publication or official exam-bank claim."""
from dataclasses import dataclass

from app.domains.content.questions.schemas import DraftContent, Provenance, fingerprint

REVIEWED_DATE = "2026-10-25"
EHS = "https://ehs.princeton.edu/"
REFERENCES = {
    "preparation": ("Princeton EHS, General Work Practices", EHS + "laboratory-research/laboratory-safety/laboratory-safety-manual/sec7"),
    "ppe": ("Princeton EHS, PPE for the Lab", EHS + "laboratory-research/laboratory-safety/ppe-the-lab"),
    "electrical": ("Princeton EHS, Electrical Safety", EHS + "laboratory-research/laboratory-safety/laboratory-safety-manual/sec7g"),
    "incident": ("Princeton EHS, Emergency Procedures", EHS + "laboratory-research/laboratory-safety/laboratory-safety-manual/sec3"),
    "labels": ("OSHA, Laboratory Standard", "https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1450"),
    "sds": ("UK HSE, Safety Data Sheets", "https://www.hse.gov.uk/coshh/basics/datasheets.htm"),
    "hood": ("Princeton EHS, Fume Hoods", EHS + "laboratory-research/laboratory-safety/laboratory-equipment-and-engineering/fume-hoods"),
    "ventilation": ("Princeton EHS, Lab Ventilation", EHS + "laboratory-research/laboratory-safety/laboratory-safety-manual/sec6b"),
    "waste": ("Princeton EHS, Chemical Waste Management", EHS + "laboratory-research/chemical-waste-management"),
    "inspection": ("Princeton EHS, Take 10 and Take Action", EHS + "take-10-and-take-action"),
}
TOPICS = {
    "entry": ("general", "入室防护", ("preparation", "ppe")),
    "electric": ("general", "设备用电", ("electrical", "inspection")),
    "emergency": ("general", "应急处置", ("incident", "preparation")),
    "storage": ("chemistry", "试剂标签储存", ("labels", "sds")),
    "ventilation": ("chemistry", "操作通风", ("hood", "ventilation")),
    "waste": ("chemistry", "废物泄漏", ("waste", "inspection", "incident")),
}


def provenance(topic):
    return Provenance(origin="derived", author="安研通项目组（AI辅助起草，待教师审核）",
        original_url=REFERENCES[TOPICS[topic][2][0]][1], acquired_date=REVIEWED_DATE,
        source_version="c1-original-draft/1", adapted=True,
        license="原创教学草稿；公开授权待项目组确认", teaching_reuse_allowed=False, public_reuse_allowed=False)


@dataclass(frozen=True)
class QuestionSeed:
    key: str
    topic: str
    group: str
    content: DraftContent
    status: str = "draft"


# Six distinct decision contexts per topic; choices are original, not copied source questions.
SINGLES = {
    "entry": [
        ("第一次进入新的实验室，准备工作的起点是什么？", "先了解本室风险和准入要求", "沿用上个实验室的习惯", "跟着同学直接操作", "不同场所的风险与要求可能不同，应先完成本室告知。"),
        ("任务要求佩戴护目镜，但现场没有合适型号，应如何处理？", "暂停操作并向教师申请合适防护", "用普通近视眼镜替代", "眯眼完成这次操作", "防护装备不满足要求时不应开始风险操作。"),
        ("选择实验手套时应优先依据什么？", "本次物质与操作的风险评估及适用性资料", "只看手套颜色", "只选最薄的款式", "防护用品须与具体风险匹配，不能仅凭外观选择。"),
        ("发现洗眼设施前堆放了纸箱，哪项行动更合适？", "报告并安排安全清障，保持应急设备可达", "等发生事故再搬走", "在纸箱上贴装饰画", "应急设备与通道需要保持可达。"),
        ("操作步骤临时改变，但新增风险尚未明确，应该怎么做？", "暂停并向教师核对风险与防护要求", "认为少一步就更安全", "直接凭经验继续", "步骤变化应重新核对风险，不能用猜测代替确认。"),
        ("同伴认为穿戴了防护就可以忽略实验规程，你会如何回应？", "仍须落实规程和工程控制", "只要手套够厚就行", "让防护用品代替所有培训", "个体防护不能代替其他必要控制措施。"),
    ],
    "electric": [
        ("接通仪器前看见电源线外皮破损，应该怎样处理？", "停止使用并报告检修", "缠一点胶带继续使用", "把破损处藏到桌后", "破损电源线应退出使用，由合格人员处理。"),
        ("仪器持续触发电气保护，哪种做法合适？", "停止使用并按规程报告排查", "绕过保护继续实验", "反复强行恢复运行", "不能通过绕过保护掩盖故障。"),
        ("发现电气设备附近有积水，应如何行动？", "远离危险区域并通知负责人员", "站入积水拔插头", "用湿布擦拭带电部位", "积水可能形成触电风险，不应贸然接触。"),
        ("插头的保护接地部件妨碍插入现有插座，应该怎么办？", "停止连接并请负责人员核对合规供电", "剪掉接地部件", "强行改造插头", "保护接地不能为方便使用而移除。"),
        ("为仪器选择供电位置时应先核对什么？", "设备要求与插座回路的适配及许可", "哪个位置最隐蔽", "能否多串联几个排插", "供电应按设备要求和回路能力核对。"),
        ("仪器断开电源后，能否直接拆开内部高压部件？", "不能，仍应由受训授权人员确认风险", "可以，断电代表没有储能", "只要戴普通手套就可以", "电容等部件可能在断电后仍有危险储能。"),
    ],
    "emergency": [
        ("进入新楼开展实验前，哪项信息应主动了解？", "报警方式、疏散路线及集合点", "仅了解教室投影仪", "只记住实验桌编号", "应预先熟悉本楼应急安排。"),
        ("火警响起且要求疏散时，哪项行动合适？", "按本楼预案及时撤离", "先等同伴拍完视频", "认为别人会先确认", "应按实际报警与疏散指令行动。"),
        ("疏散到指定集合点后，应该怎么做？", "参加人员清点并报告已知缺员信息", "立即离开且不告知任何人", "返回实验室寻找书包", "集合清点有助于避免误判人员仍在楼内。"),
        ("未经灭火训练的学生发现不明火情，首要选择是什么？", "保障自身安全，报警并按预案撤离", "靠近观察火源细节", "尝试混用不明灭火材料", "未受训者不应承担超出能力的处置任务。"),
        ("事故报告中哪组信息最有帮助？", "安全位置下报告地点、现象及已知人员情况", "只发一句出事了", "为了好看编造事故原因", "准确的已知信息比猜测原因更有利于响应。"),
        ("应急通道被临时摆放的仪器堵住，应怎样处理？", "及时报告并安排恢复通行", "认为只堵半天没关系", "在设备上贴紧急出口四字", "应急通道需要持续保持畅通。"),
    ],
    "storage": [
        ("拿到标签模糊的试剂瓶，应该怎样处理？", "停止选用并交由负责人员确认", "根据瓶子颜色判断", "打开闻气味辨别", "缺少可靠身份信息时不应猜测使用。"),
        ("准备第一次使用某试剂，哪项资料有助于风险评估？", "对应产品的安全数据表及本地规程", "仅凭同学的外号", "只看商店宣传语", "安全数据表提供危害和安全操作相关信息。"),
        ("两种试剂名称相近，能否据此认定可以混放？", "不能，应核对相容性及储存要求", "可以，名字越近越安全", "可以，只要瓶盖同色", "储存安排应根据危害与相容性，而不是名称近似。"),
        ("转移到新的长期存放容器后，哪项工作不可忽视？", "按本地规程补全准确标签", "靠记忆辨认内容", "仅贴一个笑脸", "容器标识需要让其他使用者识别内容和危险。"),
        ("供应商更新了安全数据表，应该怎么做？", "核对变化并按实验室流程更新风险资料", "一律忽略新版本", "只保留最漂亮的封面", "安全资料变化可能影响防护与储存安排。"),
        ("试剂柜中的瓶体已明显变形，应选择什么行动？", "避免擅自开启并报告负责人员", "立即开盖释放看看", "搬到公共走廊不再管", "异常容器需要由有能力的人员评估，不应试探性处理。"),
    ],
    "ventilation": [
        ("计划使用化学通风柜前，应先确认什么？", "设备状态满足本次操作要求", "柜门是否能挂衣服", "照明亮就代表通风正常", "照明状态不能代替通风功能确认。"),
        ("通风柜出现故障报警，应怎样处理？", "按规程停止相关操作并报告", "关闭声音后继续", "用纸遮住报警灯", "报警需要调查处置，不能仅消除提示。"),
        ("通风柜能否作为长期堆放无关物品的柜子？", "不能，应保持工作与气流空间", "可以，东西越满越稳定", "只要能关上玻璃窗就可以", "无关堆放可能影响通风和操作。"),
        ("需要减少有害蒸气暴露时，普通桌面风扇能否直接替代经确认的局部排风？", "不能直接替代", "可以，风越大越好", "可以，只要朝向门口", "普通风扇不提供同等的捕集与排放控制。"),
        ("实验步骤要求使用化学通风柜，学生只找到生物安全柜，应怎么做？", "暂停并请教师确认适用设备", "认为名称带安全就能替代", "同时打开两台就能替代", "不同设备的控制原理和适用范围不同。"),
        ("通风柜玻璃窗的使用位置应如何确定？", "按设备标识、规程及本次操作要求", "总是升到最高处", "根据拍摄画面决定", "操作位置应遵循经确认的设备要求。"),
    ],
    "waste": [
        ("产生实验废液前，应先明确什么？", "分类、适用容器及本地交接路径", "哪里倒掉最快", "哪种饮料瓶最顺手", "应在操作前规划废物去向。"),
        ("废液容器标签缺失，应如何处理？", "暂停加入并向负责人员核对", "看颜色猜测类别", "与所有废液合并", "未知内容不能作为相容性判断的依据。"),
        ("两类废液是否能混合，主要应依据什么？", "相容性判断及经批准的分类要求", "颜色是否一样", "哪个容器空余更多", "废物分类与相容性需要按规定确认。"),
        ("能否用化学通风柜把废溶剂蒸发掉作为常规处置？", "不能，应走规定的废物处理路径", "可以，只要没人闻到", "可以，用风扇加速更好", "通风柜不是废物处置设施。"),
        ("看见未知化学液体泄漏且自己没有处置训练，应怎么办？", "远离并警示他人，按预案报告", "凑近辨认味道", "随手加入另一种液体", "应先避免暴露，交由有能力的人员评估处置。"),
        ("等待废物收集期间，容器应如何管理？", "按本地要求做好标识、封闭和受控存放", "长期敞口放在走道", "隐藏标签避免检查", "容器应保持可识别且符合存放要求。"),
    ],
}

# Two true/false, one multi-select and one scenario per topic, in addition to six single-choice questions.
EXTRAS = {
    "entry": (("只要以前做过实验，就不需要了解新实验室的应急安排。", False), ("防护要求未确认时，应先询问教师再开始相关操作。", True),
        ("入室准备阶段应完成哪些事项？", ("了解本次风险", "确认适用防护"), "未授权先尝试设备"),
        ("同伴忘带必需防护却催促开工，你应如何选择？", "共同暂停并向教师说明", "替同伴遮挡一下就开工", "约定不拍照就开工")),
    "electric": (("为方便插入插座，可以去除设备的保护接地部件。", False), ("断电后内部部件仍可能存在储能危险。", True),
        ("设备上电前哪些情况需要停下来核对？", ("电源线破损", "设备要求与供电条件不符"), "已完成规定的检查且无异常"),
        ("同伴碰到疑似带电设备并无法脱离，你未受专业救援训练，应怎样做？", "避免直接接触并立即呼叫应急救援", "徒手拉开同伴", "先用湿拖把推设备")),
    "emergency": (("疏散后可以不报备就离开集合点。", False), ("报警时应如实说明自己已知的地点和现象。", True),
        ("应急准备应包括哪些内容？", ("了解报警方式", "确认疏散路线和集合点"), "为拿回物品规划返场路线"),
        ("你已撤离，听说还有人可能留在室内，应怎么做？", "向应急人员报告已知线索", "未经授权自行返回寻找", "把猜测当成已确认名单发布")),
    "storage": (("标签看不清时，可以靠闻气味确认未知试剂。", False), ("试剂的储存条件需要结合对应安全资料核对。", True),
        ("哪些信息有助于确认试剂使用条件？", ("准确的产品身份", "安全数据表和本地操作要求"), "同学随口起的昵称"),
        ("同桌递来一瓶无标签液体让你接着用，你应怎样做？", "停止选用并请负责人员确认", "先尝试一小口辨别", "用手摸一下再决定")),
    "ventilation": (("化学通风柜报警后，只关闭提示音就可以继续操作。", False), ("工程控制设备是否适用，需要结合具体实验确认。", True),
        ("使用通风柜时哪些做法有助于维持控制条件？", ("遵循设备标识与规程", "及时报告异常"), "遮挡报警装置"),
        ("开始操作前发现通风柜状态不明，而同伴说以前能用，应怎么做？", "暂停并请负责人员检查确认", "相信历史经验直接操作", "只增加普通风扇代替确认")),
    "waste": (("未知废液只要颜色相同就可以混合。", False), ("发现自己无能力处理的泄漏，应避免暴露并报告。", True),
        ("规范废物管理应考虑哪些事项？", ("内容与危险标识", "分类相容性和指定交接流程"), "尽量隐藏存放位置"),
        ("实验结束时容器已达到本地规定的收集限度，应如何处理？", "停止继续加入并联系负责人员按流程交接", "压缩瓶内气体腾出空间", "换到无标签饮料瓶继续收集")),
}


def question_seeds():
    result = []
    for topic, (group, title, _refs) in TOPICS.items():
        items = [("single", stem, (good, bad1, bad2), (0,), explanation)
                 for stem, good, bad1, bad2, explanation in SINGLES[topic]]
        first, second, multi, scenario = EXTRAS[topic]
        for stem, correct in (first, second):
            items.append(("true_false", stem, ("正确", "错误"), (0 if correct else 1,), "应依据本地规程、风险评估及受训授权范围行动。"))
        stem, goods, bad = multi
        items.append(("multiple", stem, (*goods, bad), (0, 1), "应同时落实所列安全控制，不能用不安全做法替代。"))
        stem, good, bad1, bad2 = scenario
        items.append(("scenario", stem, (good, bad1, bad2), (0,), "先保障人员安全，再按本地预案和负责人员指导处理。"))
        for ordinal, (kind, stem, labels, correct, explanation) in enumerate(items, start=1):
            ids = ("true", "false") if kind == "true_false" else tuple("v" + fingerprint(
                {"topic": topic, "ordinal": ordinal, "label": label})[:12] for label in labels)
            options = [{"id": key, "label": label} for key, label in zip(ids, labels, strict=True)]
            # Do not teach a fixed answer position across the demonstration bank.
            rotation = ordinal % len(options)
            options = options[rotation:] + options[:rotation]
            payload = {"kind": kind, "stem": stem, "options": options, "answer_ids": [ids[i] for i in correct],
                       "explanation": explanation, "knowledge_points": [title], "difficulty": "medium" if kind in {"multiple", "scenario"} else "easy"}
            result.append(QuestionSeed(key=f"{topic}-{ordinal:02d}", topic=topic, group=group,
                content=DraftContent(payload=payload, provenance=provenance(topic))))
    return tuple(result)


def seed_manifest():
    questions = question_seeds()
    return {"schema_version": "labconnect.c1-draft-seeds/1", "status": "draft", "reviewed_date": REVIEWED_DATE,
        "content_hash": fingerprint([{"key": item.key, "content": item.content.model_dump(mode="json")} for item in questions]),
        "references": [{"key": key, "title": title, "url": url, "author": "OSHA" if key == "labels" else "HSE" if key == "sds" else "Princeton EHS",
            "retrieved_date": REVIEWED_DATE, "publisher_version": None, "publisher_content_hash": None,
            "redistribution_license": "网页声明OGL v3.0；本包仅保存链接" if key == "sds" else "未核实；仅保存链接，不转载原文"} for key, (title, url) in REFERENCES.items()],
        "questions": [{"key": item.key, "topic": item.topic, "group": item.group, "status": item.status,
            "reference_keys": list(TOPICS[item.topic][2]), "content": item.content.model_dump(mode="json")} for item in questions]}
