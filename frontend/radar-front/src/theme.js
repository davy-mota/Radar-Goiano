export function useTema(temaClaro) {
  return {
    fundoBase: temaClaro
      ? 'bg-[radial-gradient(ellipse_70%_50%_at_15%_-10%,rgba(0,129,58,0.07),transparent),radial-gradient(ellipse_60%_50%_at_100%_0%,rgba(0,48,135,0.06),transparent)] bg-gray-50 text-gray-800'
      : 'bg-[radial-gradient(ellipse_70%_50%_at_15%_-10%,rgba(0,129,58,0.16),transparent),radial-gradient(ellipse_60%_50%_at_100%_0%,rgba(0,48,135,0.16),transparent)] bg-darkBg text-gray-200',
    menuLateral: temaClaro
      ? 'bg-white/70 backdrop-blur-lg border-gray-200/70'
      : 'bg-white/[0.04] backdrop-blur-lg border-white/10',
    card: temaClaro
      ? 'bg-white/60 backdrop-blur-md border-white/50 shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_1px_3px_rgba(0,0,0,0.05)]'
      : 'bg-white/[0.06] backdrop-blur-md border-white/[0.12] shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_10px_30px_rgba(0,0,0,0.3)]',
    titulo: temaClaro ? 'text-gray-900' : 'text-white',
    secundario: temaClaro ? 'text-gray-500' : 'text-gray-400',
    destaqueValor: temaClaro ? 'text-gray-800' : 'text-gray-100',
    campo: temaClaro
      ? 'bg-white/70 backdrop-blur-sm border-gray-300/60 text-gray-800'
      : 'bg-white/5 backdrop-blur-sm border-white/10 text-white',
    seletorAno: temaClaro
      ? 'bg-white/60 backdrop-blur-sm text-gray-800 border-gray-300/60'
      : 'bg-white/5 backdrop-blur-sm text-white border-white/10',
    cabecalhoTabela: temaClaro ? 'bg-gray-50/50' : 'bg-black/20',
    tooltip: {
      backgroundColor: temaClaro ? 'rgba(255,255,255,0.92)' : 'rgba(26,28,35,0.9)',
      borderColor: temaClaro ? 'rgba(209,213,219,0.6)' : 'rgba(255,255,255,0.1)',
      color: temaClaro ? '#1F2937' : '#FFFFFF',
    },
    graficoGrid: temaClaro ? '#e5e7eb' : '#2E323E',
    graficoTexto: temaClaro ? '#6B7280' : '#9CA3AF',
  };
}
