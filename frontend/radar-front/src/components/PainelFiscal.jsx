import { useEffect, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatarNomeProprio } from '../utils/formatarTexto.js';
import { useTema } from '../theme.js';
import ContextoTela from './ContextoTela.jsx';


const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const MESES = ['Todos', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const moeda = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 2 }).format(Number(valor || 0));
const moedaCompleta = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0));


function PainelFiscal({ anoInicial, temaClaro }) {
  const anoPadrao = anoInicial === 'todos' || Number(anoInicial) > 2025 || Number(anoInicial) < 2006 ? '2025' : anoInicial;
  const [anos, setAnos] = useState([]);
  const [ano, setAno] = useState(anoPadrao);
  const [mes, setMes] = useState('');
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/fiscal/anos`, { signal: controller.signal })
      .then((resposta) => resposta.ok ? resposta.json() : Promise.reject(new Error('Falha ao carregar os anos.')))
      .then((resultado) => setAnos(resultado.anos))
      .catch((falha) => { if (falha.name !== 'AbortError') setErro(falha.message); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const parametros = new URLSearchParams({ ano });
    if (mes) parametros.set('mes', mes);
    fetch(`${API_URL}/api/fiscal/resumo?${parametros}`, { signal: controller.signal })
      .then((resposta) => resposta.ok ? resposta.json() : Promise.reject(new Error('Não foi possível carregar os indicadores fiscais.')))
      .then(setDados)
      .catch((falha) => { if (falha.name !== 'AbortError') setErro(falha.message); })
      .finally(() => { if (!controller.signal.aborted) setCarregando(false); });
    return () => controller.abort();
  }, [ano, mes]);

  const alterarFiltro = (setter) => (evento) => {
    setCarregando(true);
    setErro('');
    setter(evento.target.value);
  };

  const { card, titulo, secundario, campo, tooltip } = useTema(temaClaro);

  return (
    <div className="animate-fade-in">
      <ContextoTela temaClaro={temaClaro} etiqueta="Capacidade de financiar políticas públicas" titulo="Orçamento e Receita" descricao="Observe quanto o Estado previu arrecadar, quanto realizou e como as despesas avançaram pelas etapas de execução." pergunta="A arrecadação e a execução da despesa estão avançando de forma compatível no período selecionado?" ressalva="A realização percentual só é exibida quando a cobertura da previsão é suficiente. Fluxos mensais podem ser sazonais e não constituem previsão do encerramento do exercício.">
        <div className="flex gap-3">
          <select aria-label="Ano fiscal" value={ano} onChange={alterarFiltro(setAno)} className={`border rounded-lg p-3 text-sm ${campo}`}>{anos.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <select aria-label="Mês fiscal" value={mes} onChange={alterarFiltro(setMes)} className={`border rounded-lg p-3 text-sm ${campo}`}>{MESES.map((nome, indice) => <option key={nome} value={indice || ''}>{nome}</option>)}</select>
        </div>
      </ContextoTela>

      {erro && <div role="alert" className="mb-6 p-4 rounded-lg border border-red-500/40 bg-red-500/10 text-red-500">{erro}</div>}
      {carregando && <div className="h-48 flex items-center justify-center"><Loader2 className="animate-spin text-goiasGreen" size={40} /></div>}

      {!carregando && dados && <>
        {!dados.receita.previsto.confiavel_para_percentual && <div className="mb-6 flex gap-3 p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-600"><AlertTriangle className="shrink-0" /><div><strong>Cobertura insuficiente da receita prevista</strong><p className="text-sm mt-1">Apenas {Number(dados.receita.previsto.cobertura_percentual).toFixed(2)}% dos registros possuem previsão positiva. O percentual de realização não será calculado para evitar interpretação enganosa.</p></div></div>}

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          <div className={`border rounded-xl p-5 ${card}`}><p className={`text-xs uppercase font-semibold ${secundario}`}>Receita prevista</p><p className="text-2xl font-bold mt-1 text-cyan-500">{moeda(dados.receita.previsto.valor)}</p><p className={`text-xs mt-1 ${secundario}`}>Cobertura: {Number(dados.receita.previsto.cobertura_percentual).toFixed(2)}%</p></div>
          <div className={`border rounded-xl p-5 ${card}`}><p className={`text-xs uppercase font-semibold ${secundario}`}>Receita arrecadada</p><p className="text-2xl font-bold mt-1 text-green-500">{moeda(dados.receita.arrecadado)}</p><p className={`text-xs mt-1 ${secundario}`}>Realização: {dados.receita.percentual_arrecadado_da_previsao == null ? '—' : `${Number(dados.receita.percentual_arrecadado_da_previsao).toFixed(1)}%`}</p></div>
          <div className={`border rounded-xl p-5 ${card}`}><p className={`text-xs uppercase font-semibold ${secundario}`}>Despesa paga</p><p className="text-2xl font-bold mt-1 text-purple-500">{moeda(dados.despesa.pago)}</p><p className={`text-xs mt-1 ${secundario}`}>Empenhado: {moeda(dados.despesa.empenhado)}</p></div>
          <div className={`border rounded-xl p-5 ${card}`}><p className={`text-xs uppercase font-semibold ${secundario}`}>Saldo observado</p><p className={`text-2xl font-bold mt-1 ${Number(dados.saldo_financeiro_observado) >= 0 ? 'text-green-500' : 'text-red-500'}`}>{moeda(dados.saldo_financeiro_observado)}</p><p className={`text-xs mt-1 ${secundario}`}>Arrecadado menos pago</p></div>
        </div>

        <div className={`border rounded-xl p-5 mb-6 ${card}`}><h3 className={`font-semibold mb-4 ${titulo}`}>Fluxo mensal observado</h3><div className="h-80"><ResponsiveContainer width="100%" height="100%"><LineChart data={dados.serie_mensal}><CartesianGrid strokeDasharray="3 3" stroke={temaClaro ? '#e5e7eb' : '#2E323E'} /><XAxis dataKey="mes" /><YAxis tickFormatter={moeda} width={75} /><Tooltip contentStyle={tooltip} formatter={moedaCompleta} /><Legend /><Line name="Arrecadado" type="monotone" dataKey="arrecadado" stroke="#00813A" strokeWidth={2} dot={false} /><Line name="Empenhado" type="monotone" dataKey="empenhado" stroke="#00D4FF" strokeWidth={2} dot={false} /><Line name="Pago" type="monotone" dataKey="pago" stroke="#8A2BE2" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
          <div className={`border rounded-xl p-5 ${card}`}><h3 className={`font-semibold mb-4 ${titulo}`}>Receita arrecadada por categoria</h3><div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={dados.top_categorias_receita.map((item) => ({ ...item, nome: formatarNomeProprio(item.nome) }))} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={temaClaro ? '#e5e7eb' : '#2E323E'} /><XAxis type="number" tickFormatter={moeda} /><YAxis type="category" dataKey="nome" width={125} fontSize={10} /><Tooltip contentStyle={tooltip} formatter={moedaCompleta} /><Bar dataKey="valor" fill="#00813A" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div></div>
          <div className={`border rounded-xl p-5 ${card}`}><h3 className={`font-semibold mb-4 ${titulo}`}>Etapas da despesa</h3><div className="space-y-5">{[['Empenhado', dados.despesa.empenhado, 'bg-cyan-500'], ['Liquidado', dados.despesa.liquidado, 'bg-purple-500'], ['Pago', dados.despesa.pago, 'bg-green-500']].map(([nome, valor, cor]) => <div key={nome}><div className="flex justify-between text-sm"><span className={titulo}>{nome}</span><strong className={titulo}>{moedaCompleta(valor)}</strong></div><div className="h-2 rounded bg-gray-500/20 mt-2"><div className={`h-full rounded ${cor}`} style={{ width: `${Math.max(0, Math.min(100, Number(valor) / Number(dados.despesa.empenhado || 1) * 100))}%` }} /></div></div>)}</div></div>
        </div>

        <p className={`text-xs ${secundario}`}>{dados.metodologia}</p>
      </>}
    </div>
  );
}

export default PainelFiscal;
