# utils/region_utils.py
import re

# 区域映射库
REGION_MAP = {
    "北非及中东": [
        "Middle East", "MENA",
        "Saudi", "Saudi Arabia", "UAE", "United Arab Emirates", "Dubai", "Abu Dhabi",
        "Oman", "Qatar", "Kuwait", "Bahrain", "Yemen", "Iraq", "Jordan", "Lebanon",
        "Syria", "Israel", "Palestine", "Iran",
        "Egypt", "Morocco", "Algeria", "Tunisia", "Libya",
    ],
    "南亚": [
        "India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal",
        "Bhutan", "Maldives", "Afghanistan",
    ],
    "东南亚": [
        "Southeast Asia", "ASEAN",
        "Vietnam", "Thailand", "Indonesia", "Malaysia", "Philippines",
        "Singapore", "Cambodia", "Myanmar", "Laos", "Brunei", "Timor-Leste",
    ],
    "东亚": [
        "East Asia", "China", "Japan", "Korea", "South Korea", "North Korea",
        "Taiwan", "Mongolia", "Hong Kong", "Macau",
    ],
    "中亚": [
        "Central Asia",
        "Kazakhstan", "Uzbekistan", "Turkmenistan", "Kyrgyzstan", "Tajikistan",
    ],
    "西欧": [
        "Western Europe",
        "UK", "Britain", "England", "Scotland", "Wales",
        "France", "Germany", "Netherlands", "Belgium",
        "Switzerland", "Ireland", "Austria", "Luxembourg",
        "Liechtenstein", "Monaco",
    ],
    "南欧": [
        "Southern Europe",
        "Spain", "Italy", "Greece", "Portugal", "Turkey",
        "Malta", "Cyprus", "Croatia", "Slovenia", "Serbia",
        "Bosnia", "Montenegro", "Albania", "Macedonia", "Kosovo",
    ],
    "北欧": [
        "Northern Europe", "Nordic", "Scandinavia",
        "Sweden", "Norway", "Denmark", "Finland", "Iceland",
        "Estonia", "Latvia", "Lithuania",
    ],
    "东欧": [
        "Eastern Europe",
        "Poland", "Hungary", "Romania", "Ukraine", "Czech",
        "Slovakia", "Bulgaria", "Belarus", "Moldova",
    ],
    "俄罗斯及高加索": [
        "Russia", "Georgia", "Armenia", "Azerbaijan",
    ],
    "拉丁美洲": [
        "Latin America", "LATAM",
        "Brazil", "Mexico", "Chile", "Argentina", "Colombia",
        "Peru", "Venezuela", "Ecuador", "Bolivia", "Paraguay",
        "Uruguay", "Costa Rica", "Panama", "Guatemala", "Honduras",
        "El Salvador", "Nicaragua", "Cuba", "Dominican Republic",
        "Puerto Rico", "Jamaica", "Trinidad",
    ],
    "北美": [
        "North America", "USA", "United States", "Canada",
    ],
    "大洋洲": [
        "Oceania", "Pacific",
        "Australia", "New Zealand", "Fiji", "Papua New Guinea",
        "Solomon Islands", "Vanuatu", "Samoa", "Tonga",
    ],
    "西非": [
        "West Africa",
        "Nigeria", "Ghana", "Senegal", "Ivory Coast", "Cote d'Ivoire",
        "Mali", "Burkina", "Burkina Faso", "Guinea", "Guinea-Bissau",
        "Sierra Leone", "Liberia", "Togo", "Benin", "Niger",
        "Mauritania", "Gambia", "Cape Verde",
    ],
    "东非": [
        "East Africa",
        "Kenya", "Ethiopia", "Tanzania", "Uganda",
        "Rwanda", "Burundi", "Somalia", "Eritrea",
        "Djibouti", "Mozambique", "Madagascar",
        "Comoros", "Seychelles", "Mauritius",
    ],
    "非洲南部": [
        "Southern Africa",
        "South Africa", "Namibia", "Zambia", "Zimbabwe",
        "Botswana", "Lesotho", "Eswatini", "Swaziland",
        "Malawi", "Angola",
    ],
    "中非及北非其他": [
        "Central Africa",
        "Congo", "DRC", "Democratic Republic", "Cameroon",
        "Central African Republic", "Chad", "Gabon",
        "Equatorial Guinea", "Sudan", "South Sudan",
    ],
}

def get_region(title):
    """根据标题判断所属区域"""
    matched = []
    for region, keywords in REGION_MAP.items():
        if any(k.lower() in title.lower() for k in keywords):
            matched.append(region)
    if not matched:
        return "全球/其他"
    return matched[0] if len(matched) == 1 else "跨区域"

def safe_slug(region):
    """生成安全的文件名slug"""
    return re.sub(r'[\\/:*?"<>|]', '_', region).replace(" ", "_")
