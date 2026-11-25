import {loadFont as carregarQuicksand} from '@remotion/google-fonts/Quicksand';
import {loadFont as carregarNunito} from '@remotion/google-fonts/NunitoSans';

const quicksand = carregarQuicksand('normal', {weights: ['700'], subsets: ['latin', 'latin-ext']});
const nunito = carregarNunito('normal', {weights: ['700', '800'], subsets: ['latin', 'latin-ext']});

export const FAMILIA_TITULO = quicksand.fontFamily;
export const FAMILIA_APOIO = nunito.fontFamily;
export const FONTE_TITULO = `${quicksand.fontFamily}, sans-serif`;
export const FONTE_APOIO = `${nunito.fontFamily}, sans-serif`;

export const fontesProntas = () => Promise.all([quicksand.waitUntilDone(), nunito.waitUntilDone()]);
