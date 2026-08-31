import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Loader2 } from 'lucide-react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatarNomeProprio } from '../utils/formatarTexto.js';
import { useTema } from '../theme.js';
import ContextoTela from './ContextoTela.jsx';


const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 2 }).format(Number(valor || 0));
const moedaCompleta = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0));
const percentual = (valor) => valor == null ? '—' : `${Number(valor).toFixed(1)}%`;


function ComparadorOrgaos({ anoInicial, temaClaro }) {
  const anoPadrao = anoInicial === 'todos' || Number(anoInicial) > 2025 ? '2025' : anoInicial;
  const [anos, setAnos] = useState([]);
  const [anoA, setAnoA] = useState(anoPadrao);
  const [anoB, setAnoB] = useState(anoPadrao);
  const [orgaosA, setOrgaosA] = useState([]);
  const [orgaosB, setOrgaosB] = useState([]);
  const [orgaoA, setOrgaoA] = useState('');
  const [orgaoB, setOrgaoB] = useState('');
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/despesas/filtros?ano=${anoA}`, { signal: controller.signal })
      .then((resposta) => resposta.ok ? resposta.json() : Promise.reject(new Error('Falha ao carregar órgãos.')))
      .then((opcoes) => {
        setAnos(opcoes.anos);
        setOrgaosA(opcoes.orgaos);
        setOrgaoA((atual) => opcoes.orgaos.includes(atual) ? atual : '');
      }).catch((falha) => { if (falha.name !== 'AbortError') setErro(falha.message); });
    return () => controller.abort();
  }, [anoA]);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/despesas/filtros?ano=${anoB}`, { signal: controller.signal })
      .then((resposta) => resposta.ok ? resposta.json() : Promise.reject(new Error('Falha ao carregar órgãos.')))
      .then((opcoes) => {
        setOrgaosB(opcoes.orgaos);
        setOrgaoB((atual) => opcoes.orgaos.includes(atual) ? atual : '');
      }).catch((falha) => { if (falha.name !== 'AbortError') setErro(falha.message); });
    return () => controller.abort();
  }, [anoB]);

  const comparar = async (evento) => {
    evento.preventDefault();
    if (!orgaoA || !orgaoB) {
      setErro('Selecione um órgão em cada cenário.');
      return;
    }
    setCarregando(true);
    setErro('');
    const parametros = new URLSearchParams({ orgao_a: orgaoA, ano_a: anoA, orgao_b: orgaoB, ano_b: anoB });
    try {
      const resposta = await fetch(`${API_URL}/api/comparacoes/orgaos?${parametros}`);
      if (!resposta.ok) throw new Error('Não foi possível comparar os cenários.');
      setDados(await resposta.json());
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  };

  const serieComparada = useMemo(() => Array.from({ length: 12 }, (_, indice) => {
    const mes = indice + 1;
    const valorA = dados?.cenario_a.serie_mensal.find((item) => item.mes === mes)?.pago || 0;
    const valorB = dados?.cenario_b.serie_mensal.find((item) => item.mes === mes)?.pago || 0;
    return { mes, cenarioA: valorA, cenarioB: valorB };
  }), [dados]);

  const { card, titulo, secundario, campo, tooltip } = useTema(temaClaro);

  const SeletorCenario = ({ rotulo, ano, setAno, orgao, setOrgao, orgaos, cor }) => (
    <div className={`border rounded-xl p-5 ${card}`}>
      <h3 className={`font-bold mb-4 ${cor}`}>{rotulo}</h3>
      <div className="grid sm:grid-cols-[120px_1fr] gap-3">
        <select aria-label={`Ano ${rotulo}`} value={ano} onChange={(e) => setAno(e.target.value)} className={`border rounded-lg p-3 text-sm ${campo}`}>{anos.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select aria-label={`Órgão ${rotulo}`} value={orgao} onChange={(e) => setOrgao(e.target.value)} className={`border rounded-lg p-3 text-sm min-w-0 ${campo}`}><option value="">Selecione o órgão</option>{orgaos.map((item) => <option key={item} value={item}>{formatarNomeProprio(item)}</option>)}</select>
      </div>
    </div>
  );

  return (
    <div className="animate-fade-in">
      <ContextoTela temaClaro={temaClaro} etiqueta="Comparação com contexto" titulo="Comparador de Órgãos e Períodos" descricao="Coloque dois órgãos ou dois exercícios lado a lado para observar diferenças de execução e concentração." pergunta="O cenário B movimentou mais ou menos recursos que o cenário A, e como essa diferença se distribuiu ao longo do ano?" ressalva="Os valores são nominais. Diferenças de atribuição, porte, cobertura e inflação podem explicar a variação; crescimento isolado não mede eficiência nem desperdício." />
      <form onSubmit={comparar} className="mb-6">
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_auto_1fr] gap-4 items-center">
          <SeletorCenario rotulo="Cenário A" ano={anoA} setAno={setAnoA} orgao={orgaoA} setOrgao={setOrgaoA} orgaos={orgaosA} cor="text-cyan-500" />
          <ArrowRight className="hidden xl:block text-gray-500" />
          <SeletorCenario rotulo="Cenário B" ano={anoB} setAno={setAnoB} orgao={orgaoB} setOrgao={setOrgaoB} orgaos={orgaosB} cor="text-purple-500" />
        </div>
        <button disabled={carregando} className="mt-4 w-full md:w-auto px-6 py-3 rounded-lg bg-goiasGreen text-white font-semibold disabled:opacity-50">{carregando ? 'Comparando...' : 'Comparar cenários'}</button>
      </form>

      {erro && <div role="alert" className="mb-6 p-4 rounded-lg border border-red-500/40 bg-red-500/10 text-red-500">{erro}</div>}
      {carregando && <div className="h-40 flex items-center justify-center"><Loader2 className="animate-spin text-goiasGreen" size={40} /></div>}

      {!carregando && dados && <>
        <div className={`border rounded-xl overflow-hidden mb-6 ${card}`}>
          <div className="overflow-x-auto"><table className="w-full text-sm"><thead className={temaClaro ? 'bg-gray-50' : 'bg-black/20'}><tr><th className={`p-4 text-left ${secundario}`}>Indicador</th><th className="p-4 text-right text-cyan-500">Cenário A</th><th className="p-4 text-right text-purple-500">Cenário B</th><th className={`p-4 text-right ${secundario}`}>Variação B/A</th></tr></thead><tbody>
            {[
              ['Empenhado', 'empenhado', moedaCompleta], ['Liquidado', 'liquidado', moedaCompleta], ['Pago', 'pago', moedaCompleta], ['Registros', 'registros', (v) => Number(v).toLocaleString('pt-BR')], ['Credores', 'credores', (v) => Number(v).toLocaleString('pt-BR')], ['Percentual pago', 'percentual_pago', percentual], ['Concentração no maior credor', 'concentracao_maior_credor', percentual],
            ].map(([rotulo, chave, formatar]) => <tr key={chave} className="border-t border-gray-500/20"><td className={`p-4 font-medium ${titulo}`}>{rotulo}</td><td className={`p-4 text-right ${titulo}`}>{formatar(dados.cenario_a.kpis[chave])}</td><td className={`p-4 text-right ${titulo}`}>{formatar(dados.cenario_b.kpis[chave])}</td><td className={`p-4 text-right font-semibold ${Number(dados.variacao_percentual_b_sobre_a[chave]) >= 0 ? 'text-amber-500' : 'text-green-500'}`}>{dados.variacao_percentual_b_sobre_a[chave] == null ? '—' : percentual(dados.variacao_percentual_b_sobre_a[chave])}</td></tr>)}
          </tbody></table></div>
        </div>

        <div className={`border rounded-xl p-5 mb-6 ${card}`}><h3 className={`font-semibold mb-4 ${titulo}`}>Valor pago por mês</h3><div className="h-80"><ResponsiveContainer width="100%" height="100%"><LineChart data={serieComparada}><CartesianGrid strokeDasharray="3 3" stroke={temaClaro ? '#e5e7eb' : '#2E323E'} /><XAxis dataKey="mes" /><YAxis tickFormatter={moeda} width={75} /><Tooltip contentStyle={tooltip} formatter={moedaCompleta} /><Legend /><Line name="Cenário A" type="monotone" dataKey="cenarioA" stroke="#00D4FF" strokeWidth={2} /><Line name="Cenário B" type="monotone" dataKey="cenarioB" stroke="#8A2BE2" strokeWidth={2} /></LineChart></ResponsiveContainer></div></div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
          {[['Cenário A', dados.cenario_a, 'text-cyan-500'], ['Cenário B', dados.cenario_b, 'text-purple-500']].map(([rotulo, cenario, cor]) => <div key={rotulo} className={`border rounded-xl p-5 ${card}`}><h3 className={`font-bold ${cor}`}>{rotulo}</h3><p className={`text-sm mb-4 truncate ${secundario}`}>{formatarNomeProprio(cenario.orgao)} · {cenario.ano}</p><h4 className={`text-xs uppercase font-semibold mb-2 ${secundario}`}>Principais credores</h4><div className="space-y-2">{cenario.top_credores.map((item) => <div key={item.nome} className="flex justify-between gap-4 text-sm"><span className={`truncate ${titulo}`}>{formatarNomeProprio(item.nome)}</span><strong className="whitespace-nowrap text-green-500">{moeda(item.valor)}</strong></div>)}</div></div>)}
        </div>
        <p className={`text-xs ${secundario}`}>{dados.metodologia} Crescimento de gasto, isoladamente, não caracteriza desperdício ou irregularidade.</p>
      </>}
    </div>
  );
}

export default ComparadorOrgaos;
