// The fake feed for the hook. Every post is invented and tagged "claim · unchecked"; none gets a verdict.
export type PostStyle = "boxes" | "invert" | "big" | "news";
export type PostBg = "stripes" | "crowd" | "monument" | "dots" | "barricade" | "static";

export type Post = {
  handle: string;
  claim: string;
  style: PostStyle;
  bg: PostBg;
  likes: number;
  comments: number;
  tags: string;
};

export const POSTS: Post[] = [
  { handle: "delhi.unfiltered", claim: "Delhi protests were illegal", style: "boxes", bg: "crowd", likes: 412_000, comments: 8_210, tags: "#delhiprotests #jantarmantar #truth" },
  { handle: "rashtra.reels", claim: "CJP wants to destabilise the country", style: "invert", bg: "monument", likes: 1_180_000, comments: 22_400, tags: "#cjp #nationfirst #wakeup" },
  { handle: "thenewsbyte", claim: "CJP is AAP's own propaganda", style: "news", bg: "stripes", likes: 286_000, comments: 5_930, tags: "#cjp #aap #exposed" },
  { handle: "ground.zero.live", claim: "People were killed in the Jantar Mantar protests", style: "big", bg: "barricade", likes: 2_040_000, comments: 61_700, tags: "#jantarmantar #justice #viral" },
  { handle: "truth.decoded", claim: "Police fired tear gas on students at Jantar Mantar", style: "boxes", bg: "static", likes: 734_000, comments: 12_100, tags: "#jantarmantar #police #students" },
  { handle: "desi.politix", claim: "Protesters were paid ₹500 each", style: "invert", bg: "crowd", likes: 958_000, comments: 30_200, tags: "#paidprotest #cjp" },
  { handle: "india.exposed", claim: "13 crore voters deleted overnight", style: "news", bg: "dots", likes: 1_620_000, comments: 44_000, tags: "#voterlist #election" },
  { handle: "breaking.bharat", claim: "Foreign money is funding the cockroach movement", style: "big", bg: "stripes", likes: 503_000, comments: 9_800, tags: "#cockroachjantaparty #foreignhand" },
  { handle: "realtalk.delhi", claim: "Internet shut down across all of Delhi", style: "boxes", bg: "monument", likes: 377_000, comments: 6_400, tags: "#delhi #internetshutdown" },
  { handle: "nation.first.news", claim: "CJP leaders have fled the country", style: "news", bg: "barricade", likes: 821_000, comments: 17_300, tags: "#cjp #breaking" },
  { handle: "viral.sach", claim: "Jantar Mantar banned forever", style: "invert", bg: "dots", likes: 1_090_000, comments: 25_600, tags: "#jantarmantar #protest" },
];

export const compact = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${Math.round(n / 100) / 10}K`.replace(".0K", "K") : `${n}`;
