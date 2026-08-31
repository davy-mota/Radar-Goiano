import { useEffect, useState } from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatarNomeProprio } from '../utils/formatarTexto.js';
import { useTema } from '../theme.js';
import ContextoTela from './ContextoTela.jsx';


const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 2 }).format(Number(valor || 0));
const moedaCompleta = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0));
const formatarCnpj = (cnpj) => cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');


function PerfilFornecedor({ documento, temaClaro, onVoltar }) {
  const [resumo, setResumo] = useState(null);
  const [contratos, setContratos] = useState([]);
  const [pagamentos, setPagamentos] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch(`${API_URL}/api/fornecedores/${documento}/resumo`, { signal: controller.signal }),
      fetch(`${API_URL}/api/fornecedores/${documento}/contratos`, { signal: controller.signal }),
    ]).then(async ([respostaResumo, respostaContratos]) => {
      if (!respostaResumo.ok || !respostaContratos.ok) throw new Error('Não foi possível montar o perfil deste fornecedor.');
      return Promise.all([respostaResumo.json(), respostaContratos.json()]);
    }).then(([novoResumo, novosContratos]) => {
      setResumo(novoResumo);
      setContratos(novosContratos.itens);
    }).catch((falha) => {
      if (falha.name !== 'AbortError') setErro(falha.message);
    }).finally(() => {
      if (!controller.signal.aborted) setCarregando(false);
    });
    return () => controller.abort();
  }, [documento]);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/fornecedores/${documento}/pagamentos?pagina=${pagina}&por_pagina=20`, { signal: controller.signal })
      .then((resposta) => {
        if (!resposta.ok) throw new Error('Não foi possível carregar os pagamentos.');
        return resposta.json();
      }).then(setPagamentos).catch((falha) => {
        if (falha.name !== 'AbortError') setErro(falha.message);
      });
    return () => controller.abort();
  }, [documento, pagina]);

  const { card, titulo, secundario, tooltip } = useTema(temaClaro);

  if (carregando) return <div className="h-72 flex items-center justify-center"><Loader2 className="animate-spin text-goiasGreen" size={42} /></div>;
  if (erro || !resumo) return <div role="alert" className="p-6 rounded-xl border border-red-500/40 bg-red-500/10 text-red-500"><button onClick={onVoltar} className="block mb-4 underline">Voltar</button>{erro || 'Fornecedor não encontrado.'}</div>;

  return (
    <div className="animate-fade-in">
      <button onClick={onVoltar} className={`flex items-center gap-2 mb-5 text-sm ${secundario}`}><ArrowLeft size={18} /> Voltar ao explorador</button>
      <ContextoTela temaClaro={temaClaro} etiqueta="Relação financeira por CNPJ" titulo={formatarNomeProprio(resumo.nome_principal)} descricao={`CNPJ ${formatarCnpj(resumo.cnpj)} · histórico consolidado dos vínculos encontrados nas bases do Radar Goiano.`} pergunta="Quanto foi empenhado e pago a este CNPJ, por quais órgãos e ao longo de quais exercícios?" ressalva="A vinculação usa CNPJ válido, não semelhança de nome. Contratos e pagamentos possuem naturezas diferentes e são apresentados separadamente; presença ou concentração não indica favorecimento indevido." />

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {[
          ['Total pago', resumo.kpis.pago],
          ['Total empenhado', resumo.kpis.empenhado],
          ['Pagamentos', Number(resumo.kpis.pagamentos).toLocaleString('pt-BR')],
          ['Órgãos pagadores', resumo.kpis.orgaos],
        ].map(([rotulo, valor], indice) => <div key={rotulo} className={`border rounded-xl p-5 ${card}`}><p className={`text-xs uppercase font-semibold ${secundario}`}>{rotulo}</p><p className={`text-xl md:text-2xl font-bold mt-1 ${indice < 2 ? 'text-green-500' : titulo}`}>{indice < 2 ? moeda(valor) : valor}</p></div>)}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <div className={`border rounded-xl p-5 ${card}`}>
          <h3 className={`font-semibold mb-4 ${titulo}`}>Evolução dos pagamentos</h3>
          <div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={resumo.evolucao_anual}><CartesianGrid strokeDasharray="3 3" stroke={temaClaro ? '#e5e7eb' : '#2E323E'} /><XAxis dataKey="ano" /><YAxis tickFormatter={moeda} width={75} /><Tooltip contentStyle={tooltip} formatter={moedaCompleta} /><Bar dataKey="pago" fill="#00813A" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </div>
        <div className={`border rounded-xl p-5 ${card}`}>
          <h3 className={`font-semibold mb-4 ${titulo}`}>Principais órgãos pagadores</h3>
          <div className="space-y-4">
            {resumo.top_orgaos.map((orgao, indice) => <div key={`${orgao.nome}-${indice}`}><div className="flex justify-between gap-4 text-sm"><span className={`truncate ${titulo}`}>{formatarNomeProprio(orgao.nome) || 'Não informado'}</span><strong className="text-green-500 whitespace-nowrap">{moeda(orgao.valor)}</strong></div><div className="h-1.5 bg-gray-500/20 rounded mt-1"><div className="h-full bg-goiasGreen rounded" style={{ width: `${Math.max(2, Number(orgao.valor) / Number(resumo.top_orgaos[0]?.valor || 1) * 100)}%` }} /></div></div>)}
          </div>
        </div>
      </div>

      <div className={`border rounded-xl p-4 mb-6 text-sm ${card}`}>
        <strong className={titulo}>Metodologia:</strong> <span className={secundario}>{resumo.metodologia} A presença neste painel não indica irregularidade.</span>
        {resumo.nomes_encontrados.length > 1 && <p className={`mt-2 ${secundario}`}>O mesmo CNPJ apareceu com {resumo.nomes_encontrados.length} variações de nome na base.</p>}
      </div>

      <div className={`border rounded-xl overflow-hidden mb-6 ${card}`}>
        <div className="p-4 border-b border-gray-500/20"><h3 className={`font-semibold ${titulo}`}>Contratos associados</h3><p className={`text-xs ${secundario}`}>{resumo.contratos.quantidade} contratos · {moedaCompleta(resumo.contratos.valor_total)}</p></div>
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead className={temaClaro ? 'bg-gray-50' : 'bg-black/20'}><tr className={secundario}><th className="p-3 text-left">Ano</th><th className="p-3 text-left">Órgão</th><th className="p-3 text-left">Contrato</th><th className="p-3 text-left">Objeto</th><th className="p-3 text-right">Valor</th></tr></thead><tbody>
          {contratos.map((item) => <tr key={item.id} className="border-t border-gray-500/20"><td className={`p-3 ${secundario}`}>{item.ano_exercicio}</td><td className={`p-3 min-w-48 ${titulo}`}>{formatarNomeProprio(item.nome_orgao)}</td><td className={`p-3 ${secundario}`}>{item.numero_contrato}</td><td className={`p-3 min-w-72 ${titulo}`}>{item.objeto_contrato}</td><td className="p-3 text-right whitespace-nowrap text-green-500 font-semibold">{moedaCompleta(item.valor_contrato)}</td></tr>)}
        </tbody></table>{!contratos.length && <p className={`p-6 text-center ${secundario}`}>Nenhum contrato foi associado por CNPJ.</p>}</div>
      </div>

      {pagamentos && <div className={`border rounded-xl overflow-hidden ${card}`}>
        <div className="p-4 border-b border-gray-500/20"><h3 className={`font-semibold ${titulo}`}>Histórico de pagamentos</h3><p className={`text-xs ${secundario}`}>{Number(pagamentos.paginacao.total).toLocaleString('pt-BR')} registros</p></div>
        <div className="overflow-x-auto"><table className="w-full text-sm"><thead className={temaClaro ? 'bg-gray-50' : 'bg-black/20'}><tr className={secundario}><th className="p-3 text-left">Data</th><th className="p-3 text-left">Órgão</th><th className="p-3 text-left">Empenho</th><th className="p-3 text-left">Descrição</th><th className="p-3 text-right">Pago</th></tr></thead><tbody>
          {pagamentos.itens.map((item) => <tr key={item.id_registro} className="border-t border-gray-500/20"><td className={`p-3 whitespace-nowrap ${secundario}`}>{item.data_emissao ? new Date(`${item.data_emissao}T00:00:00`).toLocaleDateString('pt-BR') : '—'}</td><td className={`p-3 min-w-52 ${titulo}`}>{formatarNomeProprio(item.nome_orgao)}</td><td className={`p-3 ${secundario}`}>{item.numero_empenho}</td><td className={`p-3 min-w-56 ${secundario}`}>{item.descricao}</td><td className="p-3 text-right whitespace-nowrap text-green-500 font-semibold">{moedaCompleta(item.valor_pago)}</td></tr>)}
        </tbody></table></div>
        <div className="p-4 flex justify-between items-center border-t border-gray-500/20"><button disabled={pagina === 1} onClick={() => setPagina(pagina - 1)} className="disabled:opacity-30"><ChevronLeft /></button><span className={`text-sm ${secundario}`}>Página {pagina} de {Math.max(1, pagamentos.paginacao.total_paginas)}</span><button disabled={pagina >= pagamentos.paginacao.total_paginas} onClick={() => setPagina(pagina + 1)} className="disabled:opacity-30"><ChevronRight /></button></div>
      </div>}
    </div>
  );
}

export default PerfilFornecedor;
