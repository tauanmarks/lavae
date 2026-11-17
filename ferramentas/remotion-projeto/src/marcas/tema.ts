// Tema das marcas de edição. Fonte: fichas-de-marca/marcas.json (copiado para cá por ferramentas/pipeline/gerar_ficha.py).
// Não edite marcas.json aqui: edite o original e rode o gerador.
import dados from "./marcas.json";
import * as SpaceGrotesk from "@remotion/google-fonts/SpaceGrotesk";
import * as Inter from "@remotion/google-fonts/Inter";
import * as JetBrainsMono from "@remotion/google-fonts/JetBrainsMono";
import * as ArchivoBlack from "@remotion/google-fonts/ArchivoBlack";
import * as Manrope from "@remotion/google-fonts/Manrope";
import * as DMSerifDisplay from "@remotion/google-fonts/DMSerifDisplay";
import * as Fraunces from "@remotion/google-fonts/Fraunces";
import * as Nunito from "@remotion/google-fonts/Nunito";
import * as GochiHand from "@remotion/google-fonts/GochiHand";
import * as Anton from "@remotion/google-fonts/Anton";
import * as Poppins from "@remotion/google-fonts/Poppins";
import * as SpaceMono from "@remotion/google-fonts/SpaceMono";
import * as PlayfairDisplay from "@remotion/google-fonts/PlayfairDisplay";
import * as IBMPlexSans from "@remotion/google-fonts/IBMPlexSans";
import * as IBMPlexMono from "@remotion/google-fonts/IBMPlexMono";
import * as CormorantGaramond from "@remotion/google-fonts/CormorantGaramond";
import * as Outfit from "@remotion/google-fonts/Outfit";
import * as Newsreader from "@remotion/google-fonts/Newsreader";
import * as WorkSans from "@remotion/google-fonts/WorkSans";
import * as Fredoka from "@remotion/google-fonts/Fredoka";
import * as Rubik from "@remotion/google-fonts/Rubik";
import * as Quicksand from "@remotion/google-fonts/Quicksand";
import * as NunitoSans from "@remotion/google-fonts/NunitoSans";
import * as Lexend from "@remotion/google-fonts/Lexend";

type Carregador = {
  loadFont: (estilo?: string, opcoes?: { weights?: string[]; subsets?: string[] }) => { fontFamily: string };
  getInfo: () => { subsets: string[] };
};
const MODULOS = {
  SpaceGrotesk, Inter, JetBrainsMono, ArchivoBlack, Manrope, DMSerifDisplay, Fraunces, Nunito, GochiHand, Anton, Poppins,
  SpaceMono, PlayfairDisplay, IBMPlexSans, IBMPlexMono, CormorantGaramond, Outfit, Newsreader, WorkSans, Fredoka, Rubik,
  Quicksand, NunitoSans, Lexend,
} as unknown as Record<string, Carregador>;

export type Cor = { nome: string; hex: string; uso: string };
export type EntradaLegenda = "pop" | "elastico" | "subir" | "fade" | "desfoque";
export type Codigo = {
  fontes: { titulo: string; tituloPeso: string; tituloEstilo: string; legenda: string; legendaPeso: string; apoio: string; apoioPeso: string };
  legenda: {
    modo: "bloco" | "palavra" | "frase"; tamanho: number; caixaAlta: boolean; minusculas?: boolean; contorno: number;
    corTexto: string; corContorno: string; corDestaque: string; fundoDestaque: string | null; sublinhado?: string;
    destaqueItalico?: boolean; espacamento?: number; y: number; entrada: EntradaLegenda;
  };
  zoom: { punch: number; lento: number; duracaoPunch: number };
  transicao: "corte" | "flash" | "whip" | "dissolve" | "mascara" | "luz" | "slide";
  fundoDemo: [string, string];
};
export type Marca = {
  id: string; nome: string; assinatura: string; contextos: string[]; cores: Cor[];
  legendas: { palavras_por_bloco: string }; codigo: Codigo;
};

export const MARCAS = (dados as unknown as { marcas: Marca[] }).marcas;
export const marca = (id: string): Marca => {
  const m = MARCAS.find((x) => x.id === id);
  if (!m) throw new Error(`Marca desconhecida: ${id}. Opções: ${MARCAS.map((x) => x.id).join(", ")}`);
  return m;
};

const cache = new Map<string, string>();
const carregar = (familia: string, peso: string, estilo: string): string => {
  const k = `${familia}|${peso}|${estilo}`;
  const pronto = cache.get(k);
  if (pronto) return pronto;
  const mod = MODULOS[familia];
  if (!mod) throw new Error(`Fonte sem carregador: ${familia} (adicione o import em tema.ts)`);
  const disponiveis = mod.getInfo().subsets;
  const subsets = ["latin", "latin-ext"].filter((s) => disponiveis.includes(s));
  const { fontFamily } = mod.loadFont(estilo, { weights: [peso], subsets });
  cache.set(k, fontFamily);
  return fontFamily;
};

/** Famílias CSS já carregadas para a marca. */
export const fontes = (m: Marca) => {
  const f = m.codigo.fontes;
  return {
    titulo: carregar(f.titulo, f.tituloPeso, f.tituloEstilo),
    legenda: carregar(f.legenda, f.legendaPeso, "normal"),
    apoio: carregar(f.apoio, f.apoioPeso, "normal"),
  };
};

/** Máximo de palavras por bloco de legenda (lido de "4 a 6", "1 a 3"...; frase = 10). */
export const maxPalavras = (m: Marca): number => {
  if (m.codigo.legenda.modo === "frase") return 10;
  const n = m.legendas.palavras_por_bloco.match(/(\d+)\D*$/);
  return n ? Number(n[1]) : 5;
};
