// Entrada do vídeo (props.json gerado por gerar_video.py). Todos os tempos em segundos do vídeo final.

export type Trecho = {texto: string; destaque?: boolean; t: number};

export type Bloco =
	| {tipo: 'apoio'; texto: string; t: number}
	| {tipo: 'selo'; texto: string; destaque?: boolean; t: number}
	| {tipo: 'check'; texto: string; t: number};

export type PaginaCapa = {tipo: 'capa'; inicio: number; fim: number; selo: string; titulo: Trecho[]; subtitulo?: {texto: string; t: number}};
export type PaginaDica = {tipo: 'dica'; inicio: number; fim: number; n: number; selo_topo?: {texto: string; t: number}; titulo: Trecho[]; blocos: Bloco[]};
export type PaginaFinal = {tipo: 'final'; inicio: number; fim: number; t: {logo: number; faixa: number; cena: number; horario: number; lavar: number; facil: number}};
export type Pagina = PaginaCapa | PaginaDica | PaginaFinal;

export type Entrada = {duracao: number; audio: string; paginas: Pagina[]};

// ---- layout calculado (calculateMetadata mede os textos com as fontes de verdade) ----
export type Linha = {texto: string; destaque: boolean; t: number};
export type CaixaTexto = {y: number; fonte: number; linhas: Linha[]};
export type BlocoPosto =
	| {tipo: 'apoio'; y: number; fonte: number; linhas: string[]; t: number}
	| {tipo: 'selo'; y: number; fonte: number; texto: string; destaque: boolean; t: number}
	| {tipo: 'check'; y: number; fonte: number; linhas: string[]; t: number};

export type LayoutCapa = {seloFonte: number; titulo: CaixaTexto; subtitulo?: {y: number; fonte: number}};
export type LayoutDica = {seloTopo?: {y: number; fonte: number}; titulo: CaixaTexto; tracoY: number; blocos: BlocoPosto[]; base: number};

export type Props = Entrada & {layout?: (LayoutCapa | LayoutDica | null)[]; erros?: string[]};
