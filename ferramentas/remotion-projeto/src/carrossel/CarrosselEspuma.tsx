// Carrossel de feed (1080×1350, 4:5) na marca Espuma. Cada quadro = um slide (quadro 0 = slide 1).
// Render: automacao-instagram/criar_post.py (npx remotion render CarrosselEspuma --sequence).
// Tudo estático (sem spring), porque cada slide vira uma imagem parada.
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { AZUL, CEU, FONTES_ESPUMA as F, MARINHO, NEVOA, VERDE } from "../marcas/espuma";

export type Slide =
  | { tipo: "capa"; titulo: string; destaque?: string; pilula?: string }
  | { tipo: "passo"; n: number; titulo: string; texto: string; etiqueta?: string }
  | { tipo: "dica"; titulo: string; texto: string; itens?: string[] }
  | { tipo: "final"; frase: string; chamada?: string; rodape?: string };

export type PropsCarrossel = { slides: Slide[] };

export const CARROSSEL_W = 1080;
export const CARROSSEL_H = 1350;
// Margem de segurança: a grade do perfil (3:4) corta ~34 px de cada lado; deixamos 90 px.
const MARGEM = 90;

// Bolhas só na faixa de baixo (de `de` a 88% da altura), para nunca passar por cima do texto.
const BolhasFixas: React.FC<{ seed: number; cor?: string; qtd?: number; de?: number }> = ({ seed, cor = CEU, qtd = 9, de = 62 }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    {Array.from({ length: qtd }).map((_, k) => {
      const r = Math.sin(seed * 97 + k * 13.7) * 0.5 + 0.5;
      const r2 = Math.sin(seed * 31 + k * 7.3) * 0.5 + 0.5;
      const tam = 26 + r * 70;
      return (
        <div key={k} style={{ position: "absolute", left: `${4 + r2 * 88}%`, top: `${de + r * (88 - de)}%`, width: tam, height: tam, borderRadius: "50%",
          border: `3px solid ${cor}`, background: `radial-gradient(circle at 30% 30%, #ffffffcc, ${cor}33 60%, transparent 70%)`, opacity: 0.55 }} />
      );
    })}
  </AbsoluteFill>
);

const Paginacao: React.FC<{ i: number; total: number; claro?: boolean }> = ({ i, total, claro }) => (
  <div style={{ position: "absolute", left: MARGEM, right: MARGEM, bottom: 70, display: "flex", gap: 10 }}>
    {Array.from({ length: total }).map((_, k) => (
      <div key={k} style={{ flex: 1, height: 10, borderRadius: 5, background: k < i ? VERDE : k === i ? (claro ? MARINHO : "#fff") : claro ? `${MARINHO}22` : "#ffffff55" }} />
    ))}
  </div>
);

const Logo: React.FC<{ largura: number; style?: React.CSSProperties }> = ({ largura, style }) => (
  <Img src={staticFile("lavae/logo-lavae.png")} style={{ width: largura, ...style }} />
);

const Capa: React.FC<{ s: Extract<Slide, { tipo: "capa" }>; i: number; total: number }> = ({ s, i, total }) => (
  <AbsoluteFill style={{ background: `linear-gradient(165deg, ${AZUL} 0%, #2A63C9 55%, ${CEU} 100%)` }}>
    <BolhasFixas seed={3} cor="#ffffff" qtd={10} de={50} />
    <div style={{ position: "absolute", left: MARGEM, right: MARGEM, top: 150 }}>
      <div style={{ fontFamily: F.titulo, fontSize: 118, lineHeight: 1.0, color: "#fff", textShadow: `0 8px 30px ${MARINHO}66` }}>
        {s.titulo}
        {s.destaque ? <><br /><span style={{ color: VERDE }}>{s.destaque}</span></> : null}
      </div>
      {s.pilula ? (
        <div style={{ marginTop: 44, display: "inline-block", background: "#fff", color: AZUL, fontFamily: F.titulo, fontSize: 54, padding: "12px 36px", borderRadius: 999, boxShadow: `0 12px 30px ${MARINHO}44` }}>
          {s.pilula}
        </div>
      ) : null}
    </div>
    <div style={{ position: "absolute", left: MARGEM, bottom: 130, background: "#fff", borderRadius: 28, padding: "18px 30px", boxShadow: `0 12px 30px ${MARINHO}44` }}>
      <Logo largura={300} />
    </div>
    <div style={{ position: "absolute", right: MARGEM, bottom: 150, fontFamily: F.apoio, fontSize: 36, color: "#fff" }}>arrasta →</div>
    <Paginacao i={i} total={total} />
  </AbsoluteFill>
);

const Passo: React.FC<{ s: Extract<Slide, { tipo: "passo" }>; i: number; total: number }> = ({ s, i, total }) => (
  <AbsoluteFill style={{ background: `radial-gradient(120% 90% at 20% 0%, #ffffff, ${NEVOA})` }}>
    <div style={{ position: "absolute", right: 40, bottom: 60, fontFamily: F.titulo, fontSize: 620, lineHeight: 1, color: CEU, opacity: 0.22 }}>{s.n}</div>
    <BolhasFixas seed={10 + s.n} qtd={6} de={70} />
    <div style={{ position: "absolute", left: MARGEM, right: MARGEM, top: 150 }}>
      <div style={{ width: 150, height: 150, borderRadius: 75, background: AZUL, color: "#fff", display: "grid", placeItems: "center", fontFamily: F.titulo, fontSize: 92, border: "8px solid #fff", boxShadow: `0 14px 34px ${MARINHO}44` }}>
        {s.n}
      </div>
      <div style={{ marginTop: 56, fontFamily: F.titulo, fontSize: 104, lineHeight: 1.03, color: AZUL }}>{s.titulo}</div>
      <div style={{ marginTop: 44, fontFamily: F.legenda, fontSize: 54, lineHeight: 1.3, color: MARINHO }}>{s.texto}</div>
      {s.etiqueta ? (
        <div style={{ marginTop: 44, display: "inline-flex", alignItems: "center", gap: 16, background: "#fff", color: MARINHO, fontFamily: F.apoio, fontSize: 40, padding: "14px 28px", borderRadius: 20, boxShadow: `0 8px 24px ${MARINHO}22` }}>
          <span style={{ width: 22, height: 22, borderRadius: 11, background: VERDE, display: "inline-block" }} />
          {s.etiqueta}
        </div>
      ) : null}
    </div>
    <Paginacao i={i} total={total} claro />
  </AbsoluteFill>
);

const Dica: React.FC<{ s: Extract<Slide, { tipo: "dica" }>; i: number; total: number }> = ({ s, i, total }) => (
  <AbsoluteFill style={{ background: `linear-gradient(170deg, ${AZUL}, ${CEU})` }}>
    <BolhasFixas seed={21} cor="#ffffff" qtd={7} de={74} />
    <div style={{ position: "absolute", left: MARGEM, right: MARGEM, top: 150 }}>
      <div style={{ display: "inline-block", background: VERDE, color: MARINHO, fontFamily: F.titulo, fontSize: 50, padding: "10px 32px", borderRadius: 999 }}>dica</div>
      <div style={{ marginTop: 44, fontFamily: F.titulo, fontSize: 104, lineHeight: 1.03, color: "#fff" }}>{s.titulo}</div>
      <div style={{ marginTop: 40, fontFamily: F.legenda, fontSize: 52, lineHeight: 1.3, color: "#fff" }}>{s.texto}</div>
      {s.itens?.length ? (
        <div style={{ marginTop: 44, display: "flex", flexDirection: "column", gap: 22 }}>
          {s.itens.map((t, k) => (
            <div key={k} style={{ background: "#ffffffEE", color: MARINHO, fontFamily: F.apoio, fontSize: 48, padding: "20px 32px", borderRadius: 22 }}>{t}</div>
          ))}
        </div>
      ) : null}
    </div>
    <Paginacao i={i} total={total} />
  </AbsoluteFill>
);

const Final: React.FC<{ s: Extract<Slide, { tipo: "final" }>; i: number; total: number }> = ({ s, i, total }) => (
  <AbsoluteFill style={{ background: `radial-gradient(120% 80% at 50% 30%, #ffffff, ${NEVOA})`, justifyContent: "center", alignItems: "center" }}>
    <BolhasFixas seed={9} qtd={8} de={72} />
    <Logo largura={640} />
    <div style={{ marginTop: 56, background: VERDE, color: MARINHO, fontFamily: F.titulo, fontSize: 64, padding: "16px 48px", borderRadius: 999, boxShadow: `0 12px 30px ${MARINHO}33` }}>
      {s.frase}
    </div>
    {s.chamada ? <div style={{ marginTop: 60, fontFamily: F.titulo, fontSize: 52, color: AZUL, textAlign: "center", padding: `0 ${MARGEM}px` }}>{s.chamada}</div> : null}
    {s.rodape ? <div style={{ position: "absolute", bottom: 130, left: MARGEM, right: MARGEM, textAlign: "center", fontFamily: F.apoio, fontSize: 36, color: MARINHO }}>{s.rodape}</div> : null}
    <Paginacao i={i} total={total} claro />
  </AbsoluteFill>
);

export const CarrosselEspuma: React.FC<PropsCarrossel> = ({ slides }) => {
  const i = Math.min(useCurrentFrame(), slides.length - 1);
  const s = slides[i];
  const total = slides.length;
  if (!s) return null;
  if (s.tipo === "capa") return <Capa s={s} i={i} total={total} />;
  if (s.tipo === "passo") return <Passo s={s} i={i} total={total} />;
  if (s.tipo === "dica") return <Dica s={s} i={i} total={total} />;
  return <Final s={s} i={i} total={total} />;
};

export const CARROSSEL_EXEMPLO: PropsCarrossel = {
  slides: [
    { tipo: "capa", titulo: "Primeira vez na lavanderia?", destaque: "sem complicação", pilula: "4 passos" },
    { tipo: "passo", n: 1, titulo: "Acesse o totem com o CPF", texto: "Escolha lavar ou secar.", etiqueta: "débito, crédito ou Pix" },
    { tipo: "final", frase: "lavar ficou fácil!", chamada: "Salve para a sua primeira vez" },
  ],
};
