import type {
  ChatTheme,
  Conversation,
  ConversationArtifact,
  ConversationMessage,
} from "./types";

const SQUARE = "public://mock/chat/square.svg";
const PORTRAIT = "public://mock/chat/portrait.svg";

function at(offsetMs: number): string {
  return new Date(Date.now() - offsetMs).toISOString();
}

const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;

export const CHAT_THEMES: ChatTheme[] = [
  {
    id: "saved-clay",
    name: "خمیری و بازیگوش",
    group: "saved",
    swatch: "linear-gradient(135deg, #f6c27a, #f08a5d)",
  },
  {
    id: "saved-math",
    name: "ریاضی بنفش",
    group: "saved",
    swatch: "linear-gradient(135deg, #7c3aed, #c3a7ff)",
  },
  {
    id: "catalog-clay",
    name: "Clay",
    group: "catalog",
    swatch: "linear-gradient(135deg, #e7c9a5, #d4a574)",
  },
  {
    id: "catalog-pastel",
    name: "Pastel",
    group: "catalog",
    swatch: "linear-gradient(135deg, #f8d5e0, #cde7f0)",
  },
  {
    id: "catalog-modern",
    name: "Modern",
    group: "catalog",
    swatch: "linear-gradient(135deg, #17121f, #6c6382)",
  },
];

function msg(
  conversationId: string,
  id: string,
  role: ConversationMessage["role"],
  content: string,
  language: ConversationMessage["language"],
  createdAt: string,
  extra?: ConversationMessage["metadata_json"],
): ConversationMessage {
  return {
    id,
    conversation_id: conversationId,
    role,
    content,
    language,
    created_at: createdAt,
    ...(extra ? { metadata_json: extra } : {}),
  };
}

function image(
  conversationId: string,
  id: string,
  messageId: string,
  path: string,
  aspect: ConversationArtifact["aspect_ratio"],
  createdAt: string,
  status: ConversationArtifact["status"] = "ready",
): ConversationArtifact {
  return {
    id,
    conversation_id: conversationId,
    message_id: messageId,
    artifact_type: "image",
    storage_path: status === "failed" ? null : path,
    aspect_ratio: aspect,
    status,
    created_at: createdAt,
  };
}

export function createSeedConversations(): Conversation[] {
  const decimals = at(2 * HOUR);
  const shoe = at(5 * HOUR);
  const english = at(DAY + 3 * HOUR);
  const mixed = at(3 * DAY);
  const longStart = at(5 * DAY);
  const failed = at(10 * DAY);

  const longMessages: ConversationMessage[] = [];
  for (let i = 0; i < 12; i += 1) {
    const t = at(5 * DAY - i * 4 * 60 * 1000);
    longMessages.push(
      msg(
        "conv-long",
        `long-u-${i}`,
        "user",
        i % 3 === 0
          ? "یه نسخه دیگه با توضیح ساده‌تر می‌خوام. همین تم باشه ولی متن کوتاه‌تر."
          : "تیتر قبلی بهتر بود. می‌تونی همون حس رو نگه داری؟",
        "fa",
        t,
      ),
      msg(
        "conv-long",
        `long-a-${i}`,
        "assistant",
        i % 2 === 0
          ? "باشه، با همون تم ادامه می‌دم و این بار متن رو کوتاه‌تر می‌کنم."
          : "اوکی. تیتر رو ساده‌تر می‌نویسم تا تو یک نگاه خونده بشه.",
        "fa",
        at(5 * DAY - i * 4 * 60 * 1000 - 30_000),
      ),
    );
  }

  const items: Omit<Conversation, "pinned" | "archived" | "pinned_at">[] = [
    {
      id: "conv-decimals",
      title: "ماموریت ممیز کوچولو",
      language: "fa",
      active_theme_id: "saved-clay",
      created_at: at(6 * HOUR),
      updated_at: decimals,
      messages: [
        msg(
          "conv-decimals",
          "dec-u1",
          "user",
          "برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.",
          "fa",
          at(6 * HOUR),
        ),
        msg(
          "conv-decimals",
          "dec-a1",
          "assistant",
          "حتما. یه مسیر تمیز و رنگی می‌سازم که برای دانش‌آموزها جذاب باشه ولی زیادی کودکانه نشه.",
          "fa",
          decimals,
        ),
      ],
      artifacts: [
        image("conv-decimals", "art-decimals", "dec-a1", SQUARE, "1:1", decimals),
      ],
    },
    {
      id: "conv-shoe",
      title: "تبلیغ کفش سفید",
      language: "fa",
      active_theme_id: "catalog-modern",
      created_at: at(8 * HOUR),
      updated_at: shoe,
      messages: [
        msg(
          "conv-shoe",
          "shoe-u1",
          "user",
          "برای این کفش یه تبلیغ مینیمال و لوکس بساز.",
          "fa",
          at(8 * HOUR),
        ),
        msg(
          "conv-shoe",
          "shoe-a1",
          "assistant",
          "باشه، محصول رو برجسته نگه می‌دارم و یه فضای تمیز و آروم می‌سازم.",
          "fa",
          shoe,
        ),
      ],
      artifacts: [
        image("conv-shoe", "art-shoe", "shoe-a1", PORTRAIT, "4:5", shoe),
      ],
    },
    {
      id: "conv-english",
      title: "Elegant shoe ad",
      language: "en",
      active_theme_id: "catalog-modern",
      created_at: at(DAY + 5 * HOUR),
      updated_at: english,
      messages: [
        msg(
          "conv-english",
          "en-u1",
          "user",
          "Make an elegant Instagram ad for this shoe.",
          "en",
          at(DAY + 5 * HOUR),
        ),
        msg(
          "conv-english",
          "en-a1",
          "assistant",
          "Sure — I’ll keep the shoe prominent and use a clean editorial direction.",
          "en",
          english,
        ),
      ],
      artifacts: [
        image("conv-english", "art-english", "en-a1", PORTRAIT, "4:5", english),
      ],
    },
    {
      id: "conv-mixed",
      title: "کمپین luxury",
      language: "fa",
      active_theme_id: "catalog-pastel",
      created_at: at(3 * DAY + HOUR),
      updated_at: mixed,
      messages: [
        msg(
          "conv-mixed",
          "mix-u1",
          "user",
          "برای این محصول یه luxury ad با vibe مینیمال بساز",
          "fa",
          at(3 * DAY + HOUR),
        ),
        msg(
          "conv-mixed",
          "mix-a1",
          "assistant",
          "باشه، یه نسخه مینیمال می‌سازم که حس لوکس داشته باشه ولی شلوغ نشه.",
          "fa",
          mixed,
        ),
      ],
      artifacts: [
        image("conv-mixed", "art-mixed", "mix-a1", PORTRAIT, "4:5", mixed),
      ],
    },
    {
      id: "conv-long",
      title: "تمرین کسرها",
      language: "fa",
      active_theme_id: "saved-math",
      created_at: longStart,
      updated_at: at(5 * DAY - 11 * 4 * 60 * 1000),
      messages: [
        msg(
          "conv-long",
          "long-intro-u",
          "user",
          "یه پست آموزشی بلند درباره کسرهای مساوی بساز. بعد چند بار بازنویسیش می‌کنیم.",
          "fa",
          longStart,
        ),
        msg(
          "conv-long",
          "long-intro-a",
          "assistant",
          "این نسخه رو ساختم. هر جا خواستی کوتاه‌تر یا روشن‌ترش کنیم بگو.",
          "fa",
          at(5 * DAY - 60_000),
        ),
        ...longMessages,
      ],
      artifacts: [
        image(
          "conv-long",
          "art-long",
          "long-intro-a",
          SQUARE,
          "1:1",
          at(5 * DAY - 60_000),
        ),
      ],
    },
    {
      id: "conv-failed",
      title: "کمپین نوروز",
      language: "fa",
      active_theme_id: null,
      created_at: at(10 * DAY + HOUR),
      updated_at: failed,
      messages: [
        msg(
          "conv-failed",
          "fail-u1",
          "user",
          "برای نوروز یه تصویر شاد بساز.",
          "fa",
          at(10 * DAY + HOUR),
        ),
        msg(
          "conv-failed",
          "fail-a1",
          "assistant",
          "ساخت تصویر کامل نشد. دوباره امتحان کنم؟",
          "fa",
          failed,
          { failed: true },
        ),
      ],
      artifacts: [
        image(
          "conv-failed",
          "art-failed",
          "fail-a1",
          SQUARE,
          "1:1",
          failed,
          "failed",
        ),
      ],
    },
  ];

  return items.map((item) => ({
    ...item,
    pinned: item.id === "conv-decimals",
    archived: item.id === "conv-failed",
    pinned_at: item.id === "conv-decimals" ? item.updated_at : null,
  }));
}
