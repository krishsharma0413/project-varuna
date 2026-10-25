import type { CSSProperties } from "react";
import { compact, type Post } from "../posts";
import { body, C, display, FONT, label } from "../theme";
import { Bubble, Camera, Dots, Heart, Music, Plane } from "./icons";
import { PostArt } from "./PostArt";

/** A fake Instagram-style reel. `live` 0..1 drives the like counter and progress bar. */
export const ReelPost = ({
  post,
  w,
  h,
  seed,
  live = 0,
  blurClaim = 0,
  style,
}: {
  post: Post;
  w: number;
  h: number;
  seed: number;
  live?: number;
  blurClaim?: number;
  style?: CSSProperties;
}) => {
  const len = post.claim.length;
  const size = len < 26 ? 128 : len < 36 ? 112 : 98;
  const likes = Math.round(post.likes * (0.82 + 0.18 * live));

  return (
    <div style={{ position: "absolute", width: w, height: h, overflow: "hidden", background: "#000", ...style }}>
      <PostArt bg={post.bg} w={w} h={h} seed={seed} />
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,.55) 0%, rgba(0,0,0,0) 18%, rgba(0,0,0,0) 40%, rgba(0,0,0,.9) 100%)" }} />

      {/* header */}
      <div style={{ position: "absolute", top: 112, left: 52, right: 52, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 46, color: "#fff" }}>Reels</span>
        <Camera size={54} />
      </div>

      {/* claim */}
      <div style={{ position: "absolute", left: 52, width: w - 200, top: h * 0.3, filter: blurClaim ? `blur(${blurClaim}px)` : undefined }}>
        <div
          style={{
            ...label(24, 0.06),
            display: "inline-flex",
            gap: 12,
            alignItems: "center",
            color: "#fff",
            border: "3px dashed #fff",
            padding: "8px 14px",
            marginBottom: 26,
            background: "rgba(0,0,0,.55)",
          }}
        >
          <span>?</span>
          <span>Claim · unchecked</span>
        </div>
        {post.style === "news" && (
          <div style={{ display: "flex", marginBottom: 18 }}>
            <span style={{ ...label(30, 0.1), background: "#fff", color: "#000", padding: "8px 16px" }}>Breaking</span>
            <span style={{ ...label(30, 0.1), border: "3px solid #fff", color: "#fff", padding: "5px 14px" }}>● Live</span>
          </div>
        )}
        <Claim text={post.claim} size={size} variant={post.style} />
      </div>

      {/* right rail */}
      <div style={{ position: "absolute", right: 34, bottom: 330, display: "flex", flexDirection: "column", alignItems: "center", gap: 34, color: "#fff" }}>
        <RailItem icon={<Heart size={66} fill={live > 0.55 ? "#fff" : "none"} />} text={compact(likes)} />
        <RailItem icon={<Bubble size={62} />} text={compact(post.comments)} />
        <RailItem icon={<Plane size={60} />} text="Share" />
        <Dots size={54} />
      </div>

      {/* creator + caption */}
      <div style={{ position: "absolute", left: 44, right: 170, bottom: 120, color: "#fff" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: "50%",
              border: "3px solid #fff",
              background: "repeating-linear-gradient(45deg, #fff 0 6px, #000 6px 14px)",
            }}
          />
          <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 34 }}>{post.handle}</span>
          <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 26, border: "2px solid #fff", borderRadius: 12, padding: "4px 14px" }}>Follow</span>
        </div>
        <div style={{ ...body(28), marginTop: 18, color: C.muted, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {post.tags} … more
        </div>
        <div style={{ ...body(26), marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
          <Music size={26} /> original audio · {post.handle}
        </div>
      </div>

      {/* progress */}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 64, height: 5, background: "rgba(255,255,255,.25)" }}>
        <div style={{ width: `${Math.round(live * 100)}%`, height: "100%", background: "#fff" }} />
      </div>
    </div>
  );
};

const RailItem = ({ icon, text }: { icon: React.ReactNode; text: string }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
    {icon}
    <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: 26 }}>{text}</span>
  </div>
);

const Claim = ({ text, size, variant }: { text: string; size: number; variant: Post["style"] }) => {
  if (variant === "boxes" || variant === "invert") {
    const invert = variant === "invert";
    return (
      <div style={{ ...display(size), lineHeight: 1.08 }}>
        <span
          style={{
            background: invert ? "#fff" : "#000",
            color: invert ? "#000" : "#fff",
            padding: "0.02em 0.16em",
            boxDecorationBreak: "clone",
            WebkitBoxDecorationBreak: "clone",
          }}
        >
          {text}
        </span>
      </div>
    );
  }
  return (
    <div style={{ ...display(variant === "big" ? size * 1.08 : size), color: "#fff", textShadow: "0 6px 0 #000, 0 0 40px rgba(0,0,0,.8)" }}>
      {variant === "news" ? <span style={{ borderLeft: "10px solid #fff", paddingLeft: 22, display: "block" }}>{text}</span> : text}
    </div>
  );
};
