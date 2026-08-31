import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Download, Loader2, Search } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import PerfilFornecedor from './PerfilFornecedor.jsx';
import { formatarNomeProprio } from '../utils/formatarTexto.js';
import { useTema } from '../theme.js';
import ContextoTela from './ContextoTela.jsx';


const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const MESES = ['Todos', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const moeda = (valor) => new Intl.NumberFormat('pt-BR', {
  style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 2,
}).format(Number(valor || 0));
const moedaCompleta = (valor) => new Intl.NumberFormat('pt-BR', {
  style: 'currency', currency: 'BRL',
}).format(Number(valor || 0));
const normalizarCnpj = (documento) => {
  if (!documento || !/^[0-9./-]+$/.test(documento)) return null;
  const digitos = documento.replace(/\D/g, '');
  if (digitos.length < 12 || digitos.length > 14) return null;
  const cnpj = digitos.padStart(14, '0');
  if (/^(\d)\1+$/.test(cnpj)) return null;
  const calcularDigito = (base, pesos) => {
    const soma = base.split('').reduce((total, numero, indice) => total + Number(numero) * pesos[indice], 0);
    const resto = soma % 11;
    return resto < 2 ? 0 : 11 - resto;
  };
  const primeiro = calcularDigito(cnpj.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const segundo = calcularDigito(`${cnpj.slice(0, 12)}${primeiro}`, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return cnpj.endsWith(`${primeiro}${segundo}`) ? cnpj : null;
};
const parametroInicial = (nome, padrao = '') => new URLSearchParams(window.location.search).get(nome) || padrao;


function ExploradorDespesas({ anoAtivo, temaClaro }) {
  const [mes, setMes] = useState(() => parametroInicial('mes'));
  const [orgao, setOrgao] = useState(() => parametroInicial('orgao'));
  const [buscaDigitada, setBuscaDigitada] = useState(() => parametroInicial('busca'));
  const [busca, setBusca] = useState(() => parametroInicial('busca'));
  const [pagina, setPagina] = useState(() => Math.max(1, Number(parametroInicial('pagina', '1')) || 1));
  const [opcoes, setOpcoes] = useState({ orgaos: [] });
  const [resumo, setResumo] = useState(null);
  const [listagem, setListagem] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [fornecedorSelecionado, setFornecedorSelecionado] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/despesas/filtros?ano=${anoAtivo}`, { signal: controller.signal })
      .then((resposta) => {
        if (!resposta.ok) throw new Error('Falha ao carregar filtros.');
        return resposta.json();
      })
      .then(setOpcoes)
      .catch((falha) => {
        if (falha.name !== 'AbortError') setErro(falha.message);
      });
    return () => controller.abort();
  }, [anoAtivo]);

  useEffect(() => {
    const controller = new AbortController();
    const parametros = new URLSearchParams({ ano: anoAtivo });
    if (mes) parametros.set('mes', mes);
    if (orgao) parametros.set('orgao', orgao);
    if (busca) parametros.set('busca', busca);

    const parametrosLista = new URLSearchParams(parametros);
    parametrosLista.set('pagina', pagina);
    parametrosLista.set('por_pagina', '25');

    Promise.all([
      fetch(`${API_URL}/api/despesas/resumo?${parametros}`, { signal: controller.signal }),
      fetch(`${API_URL}/api/despesas?${parametrosLista}`, { signal: controller.signal }),
    ])
      .then(async ([respostaResumo, respostaLista]) => {
        if (!respostaResumo.ok || !respostaLista.ok) {
          throw new Error('Não foi possível consultar as despesas.');
        }
        return Promise.all([respostaResumo.json(), respostaLista.json()]);
      })
      .then(([novoResumo, novaListagem]) => {
        setResumo(novoResumo);
        setListagem(novaListagem);
      })
      .catch((falha) => {
        if (falha.name !== 'AbortError') setErro(falha.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCarregando(false);
      });

    return () => controller.abort();
  }, [anoAtivo, mes, orgao, busca, pagina]);

  useEffect(() => {
    const parametros = new URLSearchParams(window.location.search);
    parametros.set('aba', 'Despesas');
    parametros.set('ano', anoAtivo);
    for (const [nome, valor] of Object.entries({ mes, orgao, busca })) {
      if (valor) parametros.set(nome, valor); else parametros.delete(nome);
    }
    if (pagina > 1) parametros.set('pagina', pagina); else parametros.delete('pagina');
    window.history.replaceState({}, '', `${window.location.pathname}?${parametros}`);
  }, [anoAtivo, mes, orgao, busca, pagina]);

  const aplicarBusca = (evento) => {
    evento.preventDefault();
    const novaBusca = buscaDigitada.trim();
    if (novaBusca === busca && pagina === 1) return;
    setCarregando(true);
    setErro('');
    setPagina(1);
    setBusca(novaBusca);
  };

  const alterarFiltro = (setter) => (evento) => {
    setCarregando(true);
    setErro('');
    setPagina(1);
    setter(evento.target.value);
  };

  const mudarPagina = (novaPagina) => {
    setCarregando(true);
    setErro('');
    setPagina(novaPagina);
  };

  const { card, titulo, secundario, campo, tooltip } = useTema(temaClaro);
  const parametrosExportacao = new URLSearchParams({ ano: anoAtivo, limite: '10000' });
  if (mes) parametrosExportacao.set('mes', mes);
  if (orgao) parametrosExportacao.set('orgao', orgao);
  if (busca) parametrosExportacao.set('busca', busca);

  if (fornecedorSelecionado) {
    return <PerfilFornecedor documento={fornecedorSelecionado} temaClaro={temaClaro} onVoltar={() => setFornecedorSelecionado(null)} />;
  }

  return (
    <div className="animate-fade-in">
      <ContextoTela temaClaro={temaClaro} etiqueta="Do resumo ao registro" titulo="Explorador de Despesas" descricao="Acompanhe as três etapas da execução financeira e consulte os pagamentos que formam os totais." pergunta="Quanto foi reservado, reconhecido e efetivamente pago — e quais registros explicam esses valores?" ressalva="Empenho, liquidação e pagamento são etapas distintas. A tabela detalhada apresenta pagamentos; ela não permite ligar cada linha, com segurança, a uma linha específica de empenho ou liquidação." />

      <div className={`border rounded-xl p-4 mb-6 ${card}`}>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          <select aria-label="Mês" value={mes} onChange={alterarFiltro(setMes)} className={`border rounded-lg p-3 text-sm ${campo}`}>
            {MESES.map((nome, indice) => <option key={nome} value={indice || ''}>{nome}</option>)}
          </select>
          <select aria-label="Órgão" value={orgao} onChange={alterarFiltro(setOrgao)} className={`border rounded-lg p-3 text-sm ${campo}`}>
            <option value="">Todos os órgãos</option>
            {opcoes.orgaos.map((item) => <option key={item} value={item}>{formatarNomeProprio(item)}</option>)}
          </select>
          <form onSubmit={aplicarBusca} className="flex gap-2">
            <input value={buscaDigitada} onChange={(e) => setBuscaDigitada(e.target.value)} maxLength={120} placeholder="Credor, CNPJ ou empenho" className={`min-w-0 flex-1 border rounded-lg p-3 text-sm ${campo}`} />
            <button aria-label="Buscar" className="px-4 rounded-lg bg-goiasGreen text-white"><Search size={18} /></button>
          </form>
        </div>
      </div>

      {erro && <div role="alert" className="mb-6 p-4 rounded-lg border border-red-500/40 bg-red-500/10 text-red-500">{erro}</div>}
      {carregando && <div className="h-48 flex items-center justify-center"><Loader2 className="animate-spin text-goiasGreen" size={40} /></div>}

      {!carregando && resumo && listagem && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            {[
              ['Empenhado', resumo.kpis.empenhado, 'text-cyan-500'],
              ['Liquidado', resumo.kpis.liquidado, 'text-purple-500'],
              ['Pago', resumo.kpis.pago, 'text-green-500'],
              ['Liquidado a pagar', resumo.kpis.a_pagar, 'text-amber-500'],
            ].map(([rotulo, valor, cor]) => (
              <div key={rotulo} className={`border rounded-xl p-5 ${card}`}>
                <p className={`text-xs font-semibold uppercase ${secundario}`}>{rotulo}</p>
                <p title={moedaCompleta(valor)} className={`text-2xl font-bold mt-1 ${cor}`}>{moeda(valor)}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
            <div className={`border rounded-xl p-4 md:p-6 ${card}`}>
              <h3 className={`font-semibold mb-4 ${titulo}`}>Execução mensal</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={resumo.serie_mensal}>
                    <CartesianGrid strokeDasharray="3 3" stroke={temaClaro ? '#e5e7eb' : '#2E323E'} />
                    <XAxis dataKey="mes" /><YAxis tickFormatter={moeda} width={75} />
                    <Tooltip contentStyle={tooltip} formatter={moedaCompleta} /><Legend />
                    <Line type="monotone" dataKey="empenhado" stroke="#00D4FF" dot={false} />
                    <Line type="monotone" dataKey="liquidado" stroke="#8A2BE2" dot={false} />
                    <Line type="monotone" dataKey="pago" stroke="#00A650" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className={`border rounded-xl p-4 md:p-6 ${card}`}>
              <h3 className={`font-semibold mb-4 ${titulo}`}>Maiores órgãos por valor pago</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={resumo.top_orgaos.map((item) => ({ ...item, nome: formatarNomeProprio(item.nome) }))} layout="vertical" margin={{ left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={temaClaro ? '#e5e7eb' : '#2E323E'} />
                    <XAxis type="number" tickFormatter={moeda} /><YAxis type="category" dataKey="nome" width={120} fontSize={10} />
                    <Tooltip contentStyle={tooltip} formatter={moedaCompleta} /><Bar dataKey="valor" fill="#00813A" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className={`border rounded-xl overflow-hidden ${card}`}>
            <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-500/20">
              <div><h3 className={`font-semibold ${titulo}`}>Registros detalhados</h3><p className={`text-xs ${secundario}`}>{Number(listagem.paginacao.total).toLocaleString('pt-BR')} resultados</p></div>
              <div className="flex items-center gap-3"><p className={`text-xs ${secundario}`}>Valores atípicos não implicam irregularidade</p><a href={`${API_URL}/api/despesas/exportar.csv?${parametrosExportacao}`} download className="flex items-center gap-2 px-3 py-2 rounded-lg bg-goiasGreen text-white text-xs font-semibold"><Download size={15} /> Exportar CSV</a></div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className={temaClaro ? 'bg-gray-50' : 'bg-black/20'}><tr className={secundario}>
                  <th className="p-3 text-left">Pagamento</th><th className="p-3 text-left">Órgão</th><th className="p-3 text-left">Credor</th><th className="p-3 text-left">Empenho</th><th className="p-3 text-right">Pago</th>
                </tr></thead>
                <tbody>
                  {listagem.itens.map((item) => <tr key={item.id_registro} className="border-t border-gray-500/20">
                    <td className={`p-3 whitespace-nowrap ${secundario}`}>{item.data_emissao ? new Date(`${item.data_emissao}T00:00:00`).toLocaleDateString('pt-BR') : '—'}</td>
                    <td className={`p-3 min-w-52 ${titulo}`}>{formatarNomeProprio(item.nome_orgao) || '—'}</td>
                    <td className="p-3 min-w-56">{normalizarCnpj(item.cnpj_cpf_credor) ? <button onClick={() => setFornecedorSelecionado(normalizarCnpj(item.cnpj_cpf_credor))} className="text-left hover:underline"><span className={`${titulo} font-medium`}>{formatarNomeProprio(item.nome_credor) || '—'}</span><br/><span className="text-xs text-goiasGreen">Ver perfil · {item.cnpj_cpf_credor}</span></button> : <><span className={titulo}>{formatarNomeProprio(item.nome_credor) || '—'}</span><br/><span className={`text-xs ${secundario}`}>{item.cnpj_cpf_credor || 'Identificador indisponível'}</span></>}</td>
                    <td className={`p-3 ${secundario}`}>{item.numero_empenho || '—'}</td>
                    <td className="p-3 text-right whitespace-nowrap font-semibold text-green-500">{moedaCompleta(item.valor_pago)}</td>
                  </tr>)}
                </tbody>
              </table>
              {!listagem.itens.length && <p className={`p-8 text-center ${secundario}`}>Nenhum registro encontrado para os filtros selecionados.</p>}
            </div>
            <div className="p-4 flex items-center justify-between border-t border-gray-500/20">
              <button disabled={pagina === 1} onClick={() => mudarPagina(pagina - 1)} className="p-2 rounded disabled:opacity-30"><ChevronLeft /></button>
              <span className={`text-sm ${secundario}`}>Página {pagina} de {Math.max(1, listagem.paginacao.total_paginas)}</span>
              <button disabled={pagina >= listagem.paginacao.total_paginas} onClick={() => mudarPagina(pagina + 1)} className="p-2 rounded disabled:opacity-30"><ChevronRight /></button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ExploradorDespesas;
