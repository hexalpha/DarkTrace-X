export type Language = "en" | "hi";

export const copy = {
  en: {
    command: "Command Center",
    overview: "Overview",
    intelligence: "Intelligence",
    hunt: "Threat Hunt",
    exposure: "Exposure Watch",
    graph: "Intel Graph",
    reports: "Reports",
    settings: "Settings",
    live: "Live telemetry",
    global: "Global threat surface",
    posture: "Security posture",
    queue: "Priority queue",
    assistant: "AI SOC Assistant",
    ask: "Ask about an IOC, CVE, or incident…",
    synthesize: "Synthesize"
  },
  hi: {
    command: "कमांड सेंटर",
    overview: "अवलोकन",
    intelligence: "इंटेलिजेंस",
    hunt: "थ्रेट हंट",
    exposure: "एक्सपोज़र वॉच",
    graph: "इंटेल ग्राफ",
    reports: "रिपोर्ट्स",
    settings: "सेटिंग्स",
    live: "लाइव टेलीमेट्री",
    global: "वैश्विक थ्रेट सतह",
    posture: "सुरक्षा स्थिति",
    queue: "प्राथमिकता कतार",
    assistant: "AI SOC सहायक",
    ask: "IOC, CVE या घटना के बारे में पूछें…",
    synthesize: "सारांश बनाएँ"
  }
} satisfies Record<Language, Record<string, string>>;

