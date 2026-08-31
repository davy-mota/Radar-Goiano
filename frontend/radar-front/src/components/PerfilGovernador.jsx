import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ContextoTela from './ContextoTela.jsx';
import { useTema } from '../theme.js';
import { formatarNomeProprio } from '../utils/formatarTexto.js';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 2 }).format(Number(valor || 0));
const moedaCompleta = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0));
const rotuloMes = (linha) => `${String(linha.mes).padStart(2, '0')}/${String(linha.ano).slice(2)}`;

export default function PerfilGovernador({ temaClaro }) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/api/governador/resumo`, { signal: controller.signal })
      .then((resposta) => {
        if (!resposta.ok) throw new Error('Não foi possível carregar o perfil do Governador.');
        return resposta.json();
      })
      .then(setDados)
      .catch((falha) => { if (falha.name !== 'AbortError') setErro(falha.message); });
    return () => controller.abort();
  }, []);

  const t = useTema(temaClaro);

  return (
    <div className="animate-fade-in">
      <ContextoTela
        temaClaro={temaClaro}
        etiqueta="Chefia do Poder Executivo"
        titulo="Quanto custa o Governador do Estado?"
        descricao="Remuneração mensal do cargo de Governador na folha de pagamento estadual, ao longo dos mandatos registrados na base, e diárias vinculadas à estrutura da Governadoria."
        pergunta="Como evoluiu a remuneração do Governador ao longo do tempo e em quais viagens a Governadoria gastou mais?"
        ressalva="Diárias listadas pertencem a cargos da Governadoria (gabinete, ajudância de ordens, segurança), não a lançamentos pessoais do Governador — a fonte oficial não publica diárias em nome do titular do cargo."
      />

      {erro && <div role="alert" className="p-4 text-red-500">{erro}</div>}
      {!erro && !dados && <div className="h-64 flex items-center justify-center"><Loader2 className="animate-spin text-goiasGreen" size={40} /></div>}

      {dados && <>
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          {[
            ['Remuneração bruta acumulada', moeda(dados.kpis.remuneracao_bruta_acumulada)],
            ['Remuneração líquida acumulada', moeda(dados.kpis.remuneracao_liquida_acumulada)],
            ['Média mensal bruta', moeda(dados.kpis.remuneracao_bruta_media_mensal)],
            ['Meses registrados', Number(dados.kpis.meses_registrados).toLocaleString('pt-BR')],
          ].map(([rotulo, valor], indice) => (
            <div key={rotulo} className={`border rounded-xl p-5 ${t.card}`}>
              <p className={`text-xs uppercase font-semibold ${t.secundario}`}>{rotulo}</p>
              <p className={`text-xl md:text-2xl font-bold mt-1 ${indice < 2 ? 'text-green-500' : t.titulo}`}>{valor}</p>
            </div>
          ))}
        </div>

        <div className={`border rounded-xl p-5 mb-6 ${t.card}`}>
          <h3 className={`font-semibold mb-1 ${t.titulo}`}>Evolução mensal da remuneração bruta</h3>
          <p className={`text-xs mb-4 ${t.secundario}`}>A linha tracejada marca o teto constitucional vigente ({moedaCompleta(dados.kpis.teto_constitucional)}).</p>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dados.evolucao_mensal.map((linha) => ({ ...linha, rotulo: rotuloMes(linha) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} />
                <XAxis dataKey="rotulo" stroke={t.graficoTexto} fontSize={10} interval={11} />
                <YAxis tickFormatter={moeda} width={75} stroke={t.graficoTexto} />
                <Tooltip contentStyle={t.tooltip} formatter={moedaCompleta} labelFormatter={(rotulo, itens) => `${formatarNomeProprio(itens?.[0]?.payload?.nome || '')} — ${rotulo}`} />
                <ReferenceLine y={dados.kpis.teto_constitucional} stroke="#EF4444" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="bruto" stroke="#00813A" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={`border rounded-xl overflow-hidden mb-6 ${t.card}`}>
          <div className="p-4 border-b border-gray-500/20"><h3 className={`font-semibold ${t.titulo}`}>Mandatos registrados na folha</h3></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className={temaClaro ? 'bg-gray-50' : 'bg-black/20'}>
                <tr className={t.secundario}><th className="p-3 text-left">Nome</th><th className="p-3 text-left">Início</th><th className="p-3 text-left">Fim</th></tr>
              </thead>
              <tbody>
                {dados.mandatos.map((mandato, indice) => (
                  <tr key={indice} className="border-t border-gray-500/20">
                    <td className={`p-3 ${t.titulo}`}>{formatarNomeProprio(mandato.nome)}</td>
                    <td className={`p-3 ${t.secundario}`}>{String(mandato.inicio.mes).padStart(2, '0')}/{mandato.inicio.ano}</td>
                    <td className={`p-3 ${t.secundario}`}>{String(mandato.fim.mes).padStart(2, '0')}/{mandato.fim.ano}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className={`border rounded-xl p-5 mb-6 ${t.card}`}>
          <h3 className={`font-semibold mb-1 ${t.titulo}`}>Diárias vinculadas à Governadoria</h3>
          <p className={`text-xs mb-4 ${t.secundario}`}>{Number(dados.diarias_governadoria.kpis.viagens).toLocaleString('pt-BR')} viagens · {moedaCompleta(dados.diarias_governadoria.kpis.total)} no total, entre gabinete, ajudância de ordens e segurança.</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dados.diarias_governadoria.por_ano}>
                <CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} />
                <XAxis dataKey="ano" stroke={t.graficoTexto} fontSize={11} />
                <YAxis tickFormatter={moeda} width={75} stroke={t.graficoTexto} />
                <Tooltip contentStyle={t.tooltip} formatter={moedaCompleta} />
                <Bar dataKey="valor" fill="#F0AB00" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={`border rounded-xl p-4 text-sm ${t.card}`}>
          <strong className={t.titulo}>Metodologia:</strong> <span className={t.secundario}>{dados.metodologia}</span>
        </div>
      </>}
    </div>
  );
}
