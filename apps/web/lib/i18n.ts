export const languageOptions = [
  { code: "en", label: "English", nativeLabel: "English" },
  { code: "hi", label: "Hindi", nativeLabel: "हिन्दी" },
  { code: "fr", label: "French", nativeLabel: "Français" },
  { code: "ru", label: "Russian", nativeLabel: "Русский" },
  { code: "ja", label: "Japanese", nativeLabel: "日本語" },
  { code: "zh", label: "Chinese", nativeLabel: "中文" },
  { code: "ur", label: "Urdu", nativeLabel: "اردو" },
  { code: "ar", label: "Arabic", nativeLabel: "العربية" },
  { code: "bn", label: "Bengali", nativeLabel: "বাংলা" },
  { code: "ta", label: "Tamil", nativeLabel: "தமிழ்" },
  { code: "te", label: "Telugu", nativeLabel: "తెలుగు" },
  { code: "mr", label: "Marathi", nativeLabel: "मराठी" }
] as const;

export type Language = typeof languageOptions[number]["code"];

const en = {
  administration: "Administration",
  anomalies: "AI Anomalies", predictive: "Threat Forecast", mcp: "MCP Servers", marketplace: "Marketplace",
  command: "Command Center",
  overview: "Overview",
  intelligence: "Intelligence",
  hunt: "Threat Hunt",
  exposure: "Exposure Watch",
  sources: "Source Management",
  documents: "Documents",
  entities: "Entities",
  events: "Events",
  crawls: "Crawl Jobs",
  assets: "Asset Discovery",
  graph: "Intel Graph",
  cves: "CVE Dashboard",
  actors: "Threat Actors",
  alerts: "Alert Center",
  aiStudio: "AI Studio",
  automations: "Automations",
  reports: "Reports",
  settings: "Settings",
  live: "Live telemetry",
  global: "Global threat surface",
  posture: "Security posture",
  queue: "Priority queue",
  assistant: "AI SOC Assistant",
  ask: "Ask about an IOC, CVE, or incident…",
  synthesize: "Synthesize"
} as const;

type Copy = Record<keyof typeof en, string>;

export const copy: Record<Language, Copy> = {
  en,
  hi: {
    ...en,
    administration: "प्रशासन", anomalies: "AI विसंगतियाँ", predictive: "खतरे का पूर्वानुमान", mcp: "MCP सर्वर", marketplace: "मार्केटप्लेस",
    command: "कमांड सेंटर", overview: "अवलोकन", intelligence: "इंटेलिजेंस", hunt: "थ्रेट हंट", exposure: "एक्सपोज़र वॉच", assets: "एसेट डिस्कवरी",
    graph: "इंटेल ग्राफ", cves: "CVE डैशबोर्ड", actors: "थ्रेट एक्टर्स", alerts: "अलर्ट सेंटर", aiStudio: "AI स्टूडियो", automations: "ऑटोमेशन",
    reports: "रिपोर्ट्स", settings: "सेटिंग्स", live: "लाइव टेलीमेट्री", global: "वैश्विक थ्रेट सतह", posture: "सुरक्षा स्थिति", queue: "प्राथमिकता कतार",
    assistant: "AI SOC सहायक", ask: "IOC, CVE या घटना के बारे में पूछें…", synthesize: "सारांश बनाएँ"
  },
  fr: {
    ...en,
    administration: "Administration", anomalies: "Anomalies IA", predictive: "Prévision des menaces", mcp: "Serveurs MCP", marketplace: "Marché",
    command: "Centre de commande", overview: "Vue d’ensemble", intelligence: "Renseignement", hunt: "Chasse aux menaces", exposure: "Surveillance de l’exposition", assets: "Découverte des actifs",
    graph: "Graphe du renseignement", cves: "Tableau CVE", actors: "Acteurs de menace", alerts: "Centre d’alertes", aiStudio: "Studio IA", automations: "Automatisations",
    reports: "Rapports", settings: "Paramètres", live: "Télémétrie en direct", global: "Surface mondiale des menaces", posture: "Posture de sécurité", queue: "File prioritaire",
    assistant: "Assistant SOC IA", ask: "Interrogez un IOC, une CVE ou un incident…", synthesize: "Synthétiser"
  },
  ru: {
    ...en,
    administration: "Администрирование", anomalies: "ИИ‑аномалии", predictive: "Прогноз угроз", mcp: "Серверы MCP", marketplace: "Маркетплейс",
    command: "Командный центр", overview: "Обзор", intelligence: "Разведка", hunt: "Поиск угроз", exposure: "Контроль экспозиции", assets: "Обнаружение активов",
    graph: "Граф разведки", cves: "Панель CVE", actors: "Атакующие", alerts: "Центр оповещений", aiStudio: "ИИ‑студия", automations: "Автоматизация",
    reports: "Отчёты", settings: "Настройки", live: "Живая телеметрия", global: "Глобальная поверхность угроз", posture: "Позиция безопасности", queue: "Очередь приоритетов",
    assistant: "ИИ‑ассистент SOC", ask: "Спросите об IOC, CVE или инциденте…", synthesize: "Синтезировать"
  },
  ja: {
    ...en,
    administration: "管理", anomalies: "AI 異常検知", predictive: "脅威予測", mcp: "MCP サーバー", marketplace: "マーケットプレイス",
    command: "コマンドセンター", overview: "概要", intelligence: "インテリジェンス", hunt: "脅威ハンティング", exposure: "露出監視", assets: "資産検出",
    graph: "インテルグラフ", cves: "CVE ダッシュボード", actors: "脅威アクター", alerts: "アラートセンター", aiStudio: "AI スタジオ", automations: "自動化",
    reports: "レポート", settings: "設定", live: "ライブテレメトリ", global: "グローバル脅威領域", posture: "セキュリティ態勢", queue: "優先キュー",
    assistant: "AI SOC アシスタント", ask: "IOC、CVE、インシデントについて質問…", synthesize: "要約"
  },
  zh: {
    ...en,
    administration: "管理", anomalies: "AI 异常检测", predictive: "威胁预测", mcp: "MCP 服务器", marketplace: "插件市场",
    command: "指挥中心", overview: "概览", intelligence: "威胁情报", hunt: "威胁狩猎", exposure: "暴露监控", assets: "资产发现",
    graph: "情报图谱", cves: "CVE 仪表盘", actors: "威胁组织", alerts: "告警中心", aiStudio: "AI 工作室", automations: "自动化",
    reports: "报告", settings: "设置", live: "实时遥测", global: "全球威胁面", posture: "安全态势", queue: "优先队列",
    assistant: "AI SOC 助手", ask: "询问 IOC、CVE 或事件…", synthesize: "生成摘要"
  },
  ur: {
    ...en,
    administration: "انتظامیہ", anomalies: "AI بے قاعدگیاں", predictive: "خطرے کی پیش گوئی", mcp: "MCP سرورز", marketplace: "مارکیٹ پلیس",
    command: "کمانڈ سینٹر", overview: "جائزہ", intelligence: "انٹیلی جنس", hunt: "خطرے کی تلاش", exposure: "ایکسپوژر واچ", assets: "اثاثہ دریافت",
    graph: "انٹیلی جنس گراف", cves: "CVE ڈیش بورڈ", actors: "خطرناک عناصر", alerts: "الرٹ سینٹر", aiStudio: "AI اسٹوڈیو", automations: "خودکاریاں",
    reports: "رپورٹس", settings: "ترتیبات", live: "لائیو ٹیلی میٹری", global: "عالمی خطرے کی سطح", posture: "سکیورٹی پوزیشن", queue: "ترجیحی قطار",
    assistant: "AI SOC معاون", ask: "IOC، CVE یا واقعے کے بارے میں پوچھیں…", synthesize: "خلاصہ بنائیں"
  },
  ar: {
    ...en,
    administration: "الإدارة", anomalies: "شذوذ الذكاء الاصطناعي", predictive: "توقع التهديدات", mcp: "خوادم MCP", marketplace: "السوق",
    command: "مركز القيادة", overview: "نظرة عامة", intelligence: "الاستخبارات", hunt: "صيد التهديدات", exposure: "مراقبة التعرض", assets: "اكتشاف الأصول",
    graph: "رسم الاستخبارات", cves: "لوحة CVE", actors: "جهات التهديد", alerts: "مركز التنبيهات", aiStudio: "استوديو الذكاء الاصطناعي", automations: "الأتمتة",
    reports: "التقارير", settings: "الإعدادات", live: "القياس الحي", global: "سطح التهديد العالمي", posture: "الوضع الأمني", queue: "قائمة الأولويات",
    assistant: "مساعد SOC بالذكاء الاصطناعي", ask: "اسأل عن IOC أو CVE أو حادثة…", synthesize: "إنشاء ملخص"
  },
  bn: {
    ...en,
    administration: "প্রশাসন", anomalies: "AI অস্বাভাবিকতা", predictive: "হুমকি পূর্বাভাস", mcp: "MCP সার্ভার", marketplace: "মার্কেটপ্লেস",
    command: "কমান্ড সেন্টার", overview: "সংক্ষিপ্তসার", intelligence: "ইন্টেলিজেন্স", hunt: "থ্রেট হান্ট", exposure: "এক্সপোজার ওয়াচ", assets: "অ্যাসেট আবিষ্কার",
    graph: "ইন্টেল গ্রাফ", cves: "CVE ড্যাশবোর্ড", actors: "থ্রেট অ্যাক্টর", alerts: "অ্যালার্ট সেন্টার", aiStudio: "AI স্টুডিও", automations: "অটোমেশন",
    reports: "রিপোর্ট", settings: "সেটিংস", live: "লাইভ টেলিমেট্রি", global: "গ্লোবাল থ্রেট সারফেস", posture: "নিরাপত্তা অবস্থা", queue: "অগ্রাধিকার সারি",
    assistant: "AI SOC সহকারী", ask: "IOC, CVE বা ঘটনা সম্পর্কে জিজ্ঞাসা করুন…", synthesize: "সারাংশ তৈরি করুন"
  },
  ta: {
    ...en,
    administration: "நிர்வாகம்", anomalies: "AI முரண்பாடுகள்", predictive: "அச்சுறுத்தல் கணிப்பு", mcp: "MCP சேவையகங்கள்", marketplace: "சந்தை",
    command: "கட்டளை மையம்", overview: "கண்ணோட்டம்", intelligence: "உளவுத்தகவல்", hunt: "அச்சுறுத்தல் வேட்டை", exposure: "வெளிப்பாடு கண்காணிப்பு", assets: "சொத்து கண்டறிதல்",
    graph: "உளவு வரைபடம்", cves: "CVE டாஷ்போர்டு", actors: "அச்சுறுத்தல் நடிகர்கள்", alerts: "எச்சரிக்கை மையம்", aiStudio: "AI ஸ்டுடியோ", automations: "தானியக்கம்",
    reports: "அறிக்கைகள்", settings: "அமைப்புகள்", live: "நேரடி டெலிமெட்ரி", global: "உலகளாவிய அச்சுறுத்தல் பரப்பு", posture: "பாதுகாப்பு நிலை", queue: "முன்னுரிமை வரிசை",
    assistant: "AI SOC உதவியாளர்", ask: "IOC, CVE அல்லது சம்பவம் பற்றி கேளுங்கள்…", synthesize: "சுருக்கம் உருவாக்கு"
  },
  te: {
    ...en,
    administration: "నిర్వహణ", anomalies: "AI అసాధారణతలు", predictive: "ముప్పు అంచనా", mcp: "MCP సర్వర్లు", marketplace: "మార్కెట్‌ప్లేస్",
    command: "కమాండ్ సెంటర్", overview: "అవలోకనం", intelligence: "ఇంటెలిజెన్స్", hunt: "థ్రెట్ హంట్", exposure: "ఎక్స్‌పోజర్ వాచ్", assets: "ఆస్తుల గుర్తింపు",
    graph: "ఇంటెల్ గ్రాఫ్", cves: "CVE డాష్‌బోర్డ్", actors: "థ్రెట్ యాక్టర్లు", alerts: "అలర్ట్ సెంటర్", aiStudio: "AI స్టూడియో", automations: "ఆటోమేషన్లు",
    reports: "రిపోర్టులు", settings: "సెట్టింగ్స్", live: "లైవ్ టెలిమెట్రీ", global: "గ్లోబల్ థ్రెట్ సర్ఫేస్", posture: "భద్రతా స్థితి", queue: "ప్రాధాన్యత క్యూ",
    assistant: "AI SOC సహాయకుడు", ask: "IOC, CVE లేదా సంఘటన గురించి అడగండి…", synthesize: "సారాంశం తయారు చేయండి"
  },
  mr: {
    ...en,
    administration: "प्रशासन", anomalies: "AI विसंगती", predictive: "धोका अंदाज", mcp: "MCP सर्व्हर्स", marketplace: "मार्केटप्लेस",
    command: "कमांड सेंटर", overview: "आढावा", intelligence: "इंटेलिजन्स", hunt: "थ्रेट हंट", exposure: "एक्सपोजर वॉच", assets: "अॅसेट शोध",
    graph: "इंटेल ग्राफ", cves: "CVE डॅशबोर्ड", actors: "थ्रेट अॅक्टर्स", alerts: "अलर्ट सेंटर", aiStudio: "AI स्टुडिओ", automations: "ऑटोमेशन",
    reports: "अहवाल", settings: "सेटिंग्ज", live: "लाइव्ह टेलिमेट्री", global: "जागतिक थ्रेट पृष्ठभाग", posture: "सुरक्षा स्थिती", queue: "प्राधान्य रांग",
    assistant: "AI SOC सहाय्यक", ask: "IOC, CVE किंवा घटनेबद्दल विचारा…", synthesize: "सारांश तयार करा"
  }
};
