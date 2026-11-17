// Elementos visuais da marca Espuma (extraídos do vídeo Lavaê aprovado em 16/11/2026, Editor_Variado).
// Use junto com LegendaMarca/ZoomMarca/TransicaoMarca (componentes.tsx) passando marca="espuma".
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { fontes, marca } from "./tema";

const M = marca("espuma");
const F = fontes(M);
export const AZUL = "#1F4BA5", CEU = "#8CC8F2", VERDE = "#8EDC3A", NEVOA = "#EAF4FC", MARINHO = "#0E2350";
export const FONTES_ESPUMA = F;

/** Bolhas subindo (transições, entrada de selos, cartões). seed muda o desenho; dur em frames. */
export const Bolhas: React.FC<{ qtd?: number; dur?: number; seed?: number; cor?: string }> = ({ qtd = 14, dur = 30, seed = 1, cor = CEU }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: qtd }).map((_, k) => {
        const r = Math.sin(seed * 97 + k * 13.7) * 0.5 + 0.5;
        const r2 = Math.sin(seed * 31 + k * 7.3) * 0.5 + 0.5;
        const atraso = r2 * dur * 0.5;
        const p = (frame - atraso) / dur;
        if (p < 0 || p > 1) return null;
        const tam = 18 + r * 46;
        return (
          <div key={k} style={{ position: "absolute", left: `${8 + r * 84}%`, top: `${100 - p * 75}%`, width: tam, height: tam, borderRadius: "50%",
            border: `3px solid ${cor}`, background: `radial-gradient(circle at 30% 30%, #ffffffcc, ${cor}33 60%, transparent 70%)`,
            opacity: interpolate(p, [0, 0.15, 0.8, 1], [0, 0.9, 0.7, 0]), transform: `translateX(${Math.sin(p * 6 + k) * 18}px)` }} />
        );
      })}
    </AbsoluteFill>
  );
};

/** Número do passo: círculo Azul Lavaê + nome do passo em pílula branca (entra deslizando). */
export const Selo: React.FC<{ n: number; texto: string; top?: number }> = ({ n, texto, top = 300 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame, fps, config: { damping: 14, stiffness: 170 } });
  return (
    <div style={{ position: "absolute", left: 56, top, display: "flex", alignItems: "center", gap: 18, transform: `translateX(${(1 - e) * -60}px)`, opacity: e }}>
      <div style={{ width: 96, height: 96, borderRadius: 48, background: AZUL, color: "#fff", display: "grid", placeItems: "center", fontFamily: F.titulo, fontSize: 58, boxShadow: "0 10px 30px #0E235066", border: "5px solid #fff" }}>{n}</div>
      <div style={{ background: "#ffffffEE", color: MARINHO, fontFamily: F.titulo, fontSize: 46, padding: "10px 24px", borderRadius: 999, boxShadow: "0 10px 30px #0E235044" }}>{texto}</div>
    </div>
  );
};

/** Barra de passos no topo: feitos em Verde Totem, atual branco, futuros translúcidos. */
export const Barra: React.FC<{ total: number; atual: number; tudo?: boolean }> = ({ total, atual, tudo }) => (
  <div style={{ position: "absolute", left: 60, right: 200, top: 236, display: "flex", gap: 10 }}>
    {Array.from({ length: total }).map((_, k) => {
      const n = k + 1;
      return <div key={n} style={{ flex: 1, height: 12, borderRadius: 6, background: tudo || n < atual ? VERDE : n === atual ? "#fff" : "#ffffff55", boxShadow: "0 2px 8px #0E235055" }} />;
    })}
  </div>
);

/** Check Verde Totem (pagamento aprovado / passo concluído). */
export const Check: React.FC<{ top?: number }> = ({ top = 520 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame, fps, config: { damping: 11, stiffness: 160 } });
  const traco = interpolate(frame, [4, 14], [60, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "center", top }}>
      <svg width={260} height={260} viewBox="0 0 100 100" style={{ transform: `scale(${e})`, filter: "drop-shadow(0 12px 24px #0E235066)" }}>
        <circle cx={50} cy={50} r={46} fill={VERDE} stroke="#fff" strokeWidth={5} />
        <path d="M28 52 L44 67 L73 36" fill="none" stroke="#fff" strokeWidth={10} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={60} strokeDashoffset={traco} />
      </svg>
    </AbsoluteFill>
  );
};

/** Etiqueta de apoio (Lexend) — valores, opções da tela, tempo de ciclo. */
export const Etiqueta: React.FC<{ texto: string; top?: number }> = ({ texto, top = 1080 }) => (
  <div style={{ position: "absolute", left: 60, top, background: "#ffffffEE", color: MARINHO, fontFamily: F.apoio, fontSize: 36, padding: "8px 20px", borderRadius: 16 }}>{texto}</div>
);

/** Título de abertura sobre o vídeo: degradê Marinho no topo, título branco + pílula verde. destaque = palavra em Azul Céu no fim. */
export const TituloAbertura: React.FC<{ linha1: string; linha2: string; destaque?: string; pilula?: string }> = ({ linha1, linha2, destaque, pilula }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame: frame - 6, fps, config: { damping: 14, stiffness: 150 } });
  const e2 = spring({ frame: frame - 18, fps, config: { damping: 14, stiffness: 150 } });
  return (
    <>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${MARINHO}CC 0%, ${MARINHO}66 32%, transparent 52%)`, opacity: e }} />
      <div style={{ position: "absolute", left: 60, right: 180, top: 300 }}>
        <div style={{ fontFamily: F.titulo, fontSize: 112, lineHeight: 0.98, color: "#fff", textShadow: `0 6px 24px ${MARINHO}`, opacity: e, transform: `translateY(${(1 - e) * 40}px)` }}>
          {linha1}<br />{linha2}{destaque ? <> <span style={{ color: CEU }}>{destaque}</span></> : null}
        </div>
        {pilula ? (
          <div style={{ marginTop: 22, display: "inline-block", background: VERDE, color: MARINHO, fontFamily: F.titulo, fontSize: 48, padding: "8px 28px", borderRadius: 999, opacity: e2, transform: `scale(${0.8 + 0.2 * e2})` }}>
            {pilula}
          </div>
        ) : null}
      </div>
    </>
  );
};

/** Cartão de tempo para pular a espera do ciclo (relógio girando + bolhas brancas). */
export const CartaoEspera: React.FC<{ linha1?: string; linha2?: string }> = ({ linha1 = "enquanto lava…", linha2 = "relaxa ☕" }) => {
  const frame = useCurrentFrame();
  const ang = frame * 6;
  const e = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ background: `linear-gradient(170deg, ${AZUL}, ${CEU})`, justifyContent: "center", alignItems: "center" }}>
      <Bolhas qtd={22} dur={60} seed={4} cor="#ffffff" />
      <svg width={200} height={200} viewBox="0 0 100 100" style={{ opacity: e, marginBottom: 40 }}>
        <circle cx={50} cy={50} r={44} fill="none" stroke="#fff" strokeWidth={6} />
        <line x1={50} y1={50} x2={50} y2={18} stroke="#fff" strokeWidth={6} strokeLinecap="round" transform={`rotate(${ang} 50 50)`} />
        <line x1={50} y1={50} x2={72} y2={50} stroke={VERDE} strokeWidth={6} strokeLinecap="round" transform={`rotate(${ang / 12} 50 50)`} />
      </svg>
      <div style={{ fontFamily: F.titulo, fontSize: 104, color: "#fff", textAlign: "center", lineHeight: 1.05, opacity: e, transform: `translateY(${(1 - e) * 30}px)` }}>
        {linha1}<br /><span style={{ color: VERDE }}>{linha2}</span>
      </div>
    </AbsoluteFill>
  );
};

/** Encerramento: logo da Lavaê sobre fundo Névoa + pílula verde. */
export const CartaoFinal: React.FC<{ frase?: string; logo?: string }> = ({ frase = "lavar ficou fácil!", logo = "lavae/logo-lavae.png" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = spring({ frame, fps, config: { damping: 13, stiffness: 140 } });
  const e2 = spring({ frame: frame - 10, fps, config: { damping: 13, stiffness: 140 } });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 30%, #ffffff, ${NEVOA})`, justifyContent: "center", alignItems: "center" }}>
      <Bolhas qtd={20} dur={70} seed={9} />
      <Img src={staticFile(logo)} style={{ width: 900, transform: `scale(${0.85 + 0.15 * e})`, opacity: e }} />
      <div style={{ marginTop: 50, background: VERDE, color: MARINHO, fontFamily: F.titulo, fontSize: 62, padding: "14px 44px", borderRadius: 999, opacity: e2, transform: `translateY(${(1 - e2) * 30}px)`, boxShadow: "0 12px 30px #0E235033" }}>
        {frase}
      </div>
    </AbsoluteFill>
  );
};

/** Volume da trilha com ducking da Espuma: 0,10 sob a fala, 0,24 sem fala, fade de 1 s / 2 s. */
export const volumeTrilha = (frame: number, fps: number, total: number, falando: (t: number) => boolean) => {
  let s = 0;
  for (let k = -6; k <= 6; k++) s += falando((frame + k) / fps) ? 0.1 : 0.24;
  const fadeIn = interpolate(frame, [0, fps], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [total - 2 * fps, total], [1, 0], { extrapolateLeft: "clamp" });
  return (s / 13) * fadeIn * fadeOut;
};
