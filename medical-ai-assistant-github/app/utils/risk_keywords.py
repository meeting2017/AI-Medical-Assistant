RISK_KEYWORDS = [
    "自杀", "自残", "轻生", "不想活", "结束生命",
    "心脏病发作", "心肌梗死", "心梗", "胸痛", "呼吸困难",
    "中风", "脑卒中", "脑出血", "脑梗", "偏瘫",
    "昏迷", "意识不清", "休克", "大出血",
    "骨折", "严重外伤", "烫伤", "烧伤",
    "中毒", "药物过量", "过敏反应", "过敏性休克",
    "癫痫发作", "抽搐", "惊厥",
    "高烧", "持续发烧", "体温过高",
    "剧烈疼痛", "无法忍受的疼痛",
    "怀孕", "流产", "宫外孕",
    "紧急", "救命", "快不行了", "撑不住了"
]

HIGH_RISK_KEYWORDS = [
    "自杀", "自残", "轻生", "不想活", "结束生命",
    "心脏病发作", "心肌梗死", "心梗", "中风", "脑卒中", "脑出血", "脑梗",
    "昏迷", "意识不清", "休克", "大出血", "中毒", "药物过量", "过敏性休克",
    "紧急", "救命", "快不行了"
]

MEDIUM_RISK_KEYWORDS = [
    "胸痛", "呼吸困难", "偏瘫", "骨折", "严重外伤", "烫伤", "烧伤",
    "癫痫发作", "抽搐", "惊厥", "高烧", "持续发烧", "剧烈疼痛"
]

LOW_RISK_KEYWORDS = [
    "怀孕", "流产", "宫外孕", "无法忍受的疼痛", "撑不住了"
]

def check_risk_level(text: str) -> str:
    text_lower = text.lower()
    
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text_lower:
            return "HIGH"
    
    for keyword in MEDIUM_RISK_KEYWORDS:
        if keyword in text_lower:
            return "MEDIUM"
    
    for keyword in LOW_RISK_KEYWORDS:
        if keyword in text_lower:
            return "LOW"
    
    return "SAFE"

def get_risk_keywords_by_level(level: str) -> list:
    level = level.upper()
    if level == "HIGH":
        return HIGH_RISK_KEYWORDS
    elif level == "MEDIUM":
        return MEDIUM_RISK_KEYWORDS
    elif level == "LOW":
        return LOW_RISK_KEYWORDS
    return []