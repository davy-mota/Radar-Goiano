import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid } from 'recharts';
import { AlertTriangle, LayoutDashboard, FileText, Plane, Users, Loader2, Sun, Moon, Menu, X, WalletCards, Scale, Landmark, ShieldAlert, Database, Building2, ScrollText, Crown, Vote } from 'lucide-react';
import ExploradorDespesas from './components/ExploradorDespesas.jsx';
import ComparadorOrgaos from './components/ComparadorOrgaos.jsx';
import PainelFiscal from './components/PainelFiscal.jsx';
import CentralAlertas from './components/CentralAlertas.jsx';
import QualidadeDados from './components/QualidadeDados.jsx';
import ResumoCidadao from './components/ResumoCidadao.jsx';
import ContextoTela from './components/ContextoTela.jsx';
import PoliticasPublicas from './components/PoliticasPublicas.jsx';
import RepassesMunicipais from './components/RepassesMunicipais.jsx';
import EmendasParlamentares from './components/EmendasParlamentares.jsx';
import PerfilGovernador from './components/PerfilGovernador.jsx';
import ParlamentaresGoias from './components/ParlamentaresGoias.jsx';
import { formatarNomeProprio } from './utils/formatarTexto.js';
import { useTema } from './theme.js';

const CORES_GRAFICOS = ['#00D4FF', '#8A2BE2', '#FF007F', '#00FA9A', '#FFA500'];
const formatarMoeda = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor || 0);

function App() {
  const parametrosIniciais = new URLSearchParams(window.location.search);
  const abasValidas = ['Visão Geral', 'Despesas', 'Políticas', 'Repasses', 'Emendas', 'Governador', 'Parlamentares', 'Comparador', 'Fiscal', 'Alertas', 'Qualidade', 'Contratos', 'Diárias', 'Folha'];
  const abaInicial = parametrosIniciais.get('aba');
  const [abaAtiva, setAbaAtiva] = useState(abasValidas.includes(abaInicial) ? abaInicial : 'Visão Geral');
  const [carregando, setCarregando] = useState(false);
  const [anoAtivo, setAnoAtivo] = useState(parametrosIniciais.get('ano') || 'todos');
  const [temaClaro, setTemaClaro] = useState(false);
  const [menuAberto, setMenuAberto] = useState(false);

  const [dadosGerais, setDadosGerais] = useState(null);
  const [dadosContratos, setDadosContratos] = useState(null);
  const [dadosFolha, setDadosFolha] = useState(null);
  const [dadosDiarias, setDadosDiarias] = useState(null);

  const handleMudarAno = (novoAno) => {
    setAnoAtivo(novoAno);
    setDadosGerais(null);
    setDadosContratos(null);
    setDadosFolha(null);
    setDadosDiarias(null);
    const parametros = new URLSearchParams(window.location.search);
    parametros.set('ano', novoAno);
    window.history.replaceState({}, '', `${window.location.pathname}?${parametros}`);
  };

  const mudarAba = (nomeAba) => {
    setAbaAtiva(nomeAba);
    setMenuAberto(false);
    const parametros = new URLSearchParams();
    parametros.set('aba', nomeAba);
    parametros.set('ano', anoAtivo);
    window.history.replaceState({}, '', `${window.location.pathname}?${parametros}`);
  };

  const recarregarDados = () => {
    if (abaAtiva === 'Visão Geral') setDadosGerais(null);
    if (abaAtiva === 'Contratos') setDadosContratos(null);
    if (abaAtiva === 'Folha') setDadosFolha(null);
    if (abaAtiva === 'Diárias') setDadosDiarias(null);
  };

  useEffect(() => {
    let isMounted = true; 
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 15000);

    const buscarDados = async () => {
      let url = "";
      let setDadosAtuais = null;

      if (abaAtiva === 'Visão Geral' && !dadosGerais) { 
        url = `/dados/cache_visao_geral_${anoAtivo}.json`; 
        setDadosAtuais = setDadosGerais; 
      }
      else if (abaAtiva === 'Contratos' && !dadosContratos) { 
        url = `/dados/cache_contratos_${anoAtivo}.json`; 
        setDadosAtuais = setDadosContratos; 
      }
      else if (abaAtiva === 'Folha' && !dadosFolha) { 
        url = `/dados/cache_folha_${anoAtivo}.json`; 
        setDadosAtuais = setDadosFolha; 
      }
      else if (abaAtiva === 'Diárias' && !dadosDiarias) { 
        url = `/dados/cache_diarias_${anoAtivo}.json`; 
        setDadosAtuais = setDadosDiarias; 
      }

      if (url && setDadosAtuais) {
        setCarregando(true);
        try {
          const urlSemCache = `${url}?t=${new Date().getTime()}`;
          const resposta = await fetch(urlSemCache, { signal: abortController.signal });
          clearTimeout(timeoutId); 
          
          if (!resposta.ok) throw new Error("Arquivo JSON não encontrado.");
          
          const dados = await resposta.json();
          if (isMounted) setDadosAtuais(dados);

        } catch (erro) {
          if (!isMounted) return; 
          if (erro.name === 'AbortError') {
            setDadosAtuais({ erro: "⏳ Tempo de carregamento excedido." });
          } else {
            setDadosAtuais({ erro: `📄 Os dados para '${anoAtivo}' ainda não foram processados.` });
          }
        } finally {
          if (isMounted) setCarregando(false);
        }
      }
    };

    buscarDados();

    return () => {
      isMounted = false; 
      clearTimeout(timeoutId);
      abortController.abort();
    };
  }, [abaAtiva, anoAtivo, dadosGerais, dadosContratos, dadosFolha, dadosDiarias]);

  const tema = useTema(temaClaro);
  const t = {
    ...tema,
    subtitulo: tema.secundario,
    tooltipBg: tema.tooltip.backgroundColor,
    tooltipBorder: tema.tooltip.borderColor,
    tooltipTexto: tema.tooltip.color,
  };

  const dadosDaAba = {
    'Visão Geral': dadosGerais,
    Contratos: dadosContratos,
    Folha: dadosFolha,
    Diárias: dadosDiarias,
  }[abaAtiva];

  const cssBotao = (nome) => `flex items-center gap-3 w-full px-4 py-3 rounded-lg transition-colors text-left ${
    abaAtiva === nome 
      ? (temaClaro ? "bg-green-100 text-green-700 border border-green-300 font-medium" : "bg-goiasGreen/10 text-goiasGreen border border-goiasGreen/30") 
      : (temaClaro ? "text-gray-600 hover:text-green-700 hover:bg-gray-100 border border-transparent" : "text-gray-400 hover:text-white hover:bg-darkCard border border-transparent")
  }`;

  return (
    <div className={`flex h-screen font-sans overflow-hidden transition-colors duration-300 ${t.fundoBase}`}>
      
      {menuAberto && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm transition-opacity" 
          onClick={() => setMenuAberto(false)}
        />
      )}

      <aside className={`fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-300 flex flex-col border-r md:relative md:translate-x-0 md:w-64 ${menuAberto ? 'translate-x-0' : '-translate-x-full'} ${t.menuLateral}`}>
        <div className="p-6 relative">
          <button className={`absolute top-6 right-4 md:hidden ${t.titulo}`} onClick={() => setMenuAberto(false)}>
            <X size={24} />
          </button>

          <div className="flex items-center gap-3 mb-4 mt-2 md:mt-0">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Flag_of_Goi%C3%A1s.svg/1280px-Flag_of_Goi%C3%A1s.svg.png" alt="Bandeira de Goiás" className="h-6 rounded-sm shadow-sm" />
            <h1 className={`text-2xl font-bold ${temaClaro ? 'text-gray-900' : 'bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400'}`}>Radar Goiano</h1>
          </div>
          <p className={`text-xs mb-4 ${t.subtitulo}`}>Auditoria de Contas Públicas</p>

          <div className={`border rounded-lg p-1 transition-colors ${t.seletorAno}`}>
            <select value={anoAtivo} onChange={(e) => handleMudarAno(e.target.value)} className="w-full bg-transparent text-sm p-2 outline-none cursor-pointer font-medium">
              <option value="todos" className={temaClaro ? "bg-white" : "bg-darkCard text-goiasYellow"}>🌟 Todos os Anos</option>
              {Array.from({ length: 2026 - 2013 + 1 }, (_, i) => 2026 - i).map(ano => (
                <option key={ano} value={ano.toString()} className={temaClaro ? "bg-white" : "bg-darkCard"}>Exercício {ano}</option>
              ))}
            </select>
          </div>
        </div>        
        
        <nav className="flex-1 px-4 space-y-2 overflow-y-auto">
          <button onClick={() => mudarAba('Visão Geral')} className={cssBotao('Visão Geral')}><LayoutDashboard size={20} /> Visão Geral</button>
          <button onClick={() => mudarAba('Despesas')} className={cssBotao('Despesas')}><WalletCards size={20} /> Explorar Despesas</button>
          <button onClick={() => mudarAba('Políticas')} className={cssBotao('Políticas')}><Landmark size={20} /> Políticas Públicas</button>
          <button onClick={() => mudarAba('Repasses')} className={cssBotao('Repasses')}><Building2 size={20} /> Repasses Municipais</button>
          <button onClick={() => mudarAba('Emendas')} className={cssBotao('Emendas')}><ScrollText size={20} /> Emendas Parlamentares</button>
          <button onClick={() => mudarAba('Governador')} className={cssBotao('Governador')}><Crown size={20} /> Governador</button>
          <button onClick={() => mudarAba('Parlamentares')} className={cssBotao('Parlamentares')}><Vote size={20} /> Deputados e Senadores</button>
          <button onClick={() => mudarAba('Comparador')} className={cssBotao('Comparador')}><Scale size={20} /> Comparar Órgãos</button>
          <button onClick={() => mudarAba('Fiscal')} className={cssBotao('Fiscal')}><Landmark size={20} /> Orçamento e Receita</button>
          <button onClick={() => mudarAba('Alertas')} className={cssBotao('Alertas')}><ShieldAlert size={20} /> Central de Alertas</button>
          <button onClick={() => mudarAba('Qualidade')} className={cssBotao('Qualidade')}><Database size={20} /> Qualidade dos Dados</button>
          <button onClick={() => mudarAba('Contratos')} className={cssBotao('Contratos')}><FileText size={20} /> Contratos</button>
          <button onClick={() => mudarAba('Diárias')} className={cssBotao('Diárias')}><Plane size={20} /> Diárias e Viagens</button>
          <button onClick={() => mudarAba('Folha')} className={cssBotao('Folha')}><Users size={20} /> Folha de Pagamento</button>
        </nav>

        <div className="p-4 border-t border-gray-200 dark:border-darkBorder">
          <button onClick={() => setTemaClaro(!temaClaro)} className={`flex items-center justify-center gap-2 w-full py-3 md:py-2 rounded-lg transition-colors border shadow-sm ${temaClaro ? "bg-gray-100 text-gray-700 hover:bg-gray-200 border-gray-300" : "bg-darkCard text-gray-400 hover:text-white border-darkBorder hover:bg-gray-800"}`}>
            {temaClaro ? <Moon size={18} /> : <Sun size={18} />}
            <span className="text-sm font-medium">{temaClaro ? "Modo Escuro" : "Modo Claro"}</span>
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col w-full overflow-hidden">
        <header className={`md:hidden flex items-center justify-between p-4 border-b z-30 shadow-sm ${t.menuLateral}`}>
          <div className="flex items-center gap-3">
            <button onClick={() => setMenuAberto(true)} className={`p-1 rounded-md ${temaClaro ? 'hover:bg-gray-100 text-gray-800' : 'hover:bg-gray-800 text-white'}`}>
              <Menu size={26} />
            </button>
            <h1 className={`text-xl font-bold ${t.titulo}`}>Radar Goiano</h1>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <div role="status" className={`mb-5 flex items-start gap-3 rounded-xl border p-4 text-sm ${temaClaro ? 'bg-emerald-50 border-emerald-300 text-emerald-900' : 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200'}`}>
            <AlertTriangle size={20} className="shrink-0 mt-0.5" />
            <p><strong>Base auditada e versionada:</strong> pagamentos e receitas são servidos pela versão validada ativa. Os alertas apresentados são indícios analíticos e sempre exigem verificação na fonte oficial.</p>
          </div>

          {carregando && (
            <div className="flex flex-col items-center justify-center h-64"><Loader2 className="w-12 h-12 text-goiasGreen animate-spin mb-4" /></div>
          )}

          {!carregando && dadosDaAba?.erro && (
            <div role="alert" className={`max-w-xl mx-auto mt-16 border rounded-xl p-6 text-center ${temaClaro ? 'bg-red-50 border-red-200 text-red-800' : 'bg-darkCard border-red-900/50 text-red-300'}`}>
              <h2 className="text-lg font-bold mb-2">Não foi possível carregar os dados</h2>
              <p className="text-sm mb-5">{dadosDaAba.erro}</p>
              <button type="button" onClick={recarregarDados} className="px-4 py-2 rounded-lg bg-goiasGreen text-white font-semibold hover:opacity-90">
                Tentar novamente
              </button>
            </div>
          )}

          {abaAtiva === 'Despesas' && (
            <ExploradorDespesas key={anoAtivo} anoAtivo={anoAtivo} temaClaro={temaClaro} />
          )}

          {abaAtiva === 'Comparador' && (
            <ComparadorOrgaos anoInicial={anoAtivo} temaClaro={temaClaro} />
          )}

          {abaAtiva === 'Fiscal' && (
            <PainelFiscal anoInicial={anoAtivo} temaClaro={temaClaro} />
          )}

          {abaAtiva === 'Alertas' && (
            <CentralAlertas anoInicial={anoAtivo} temaClaro={temaClaro} />
          )}

          {abaAtiva === 'Qualidade' && (
            <QualidadeDados temaClaro={temaClaro} />
          )}

          {abaAtiva === 'Visão Geral' && dadosGerais?.kpis && !carregando && (
            <ResumoCidadao dados={dadosGerais} ano={anoAtivo} temaClaro={temaClaro} navegar={mudarAba} />
          )}

          {abaAtiva === 'Políticas' && <PoliticasPublicas temaClaro={temaClaro} />}
          {abaAtiva === 'Repasses' && <RepassesMunicipais temaClaro={temaClaro} />}
          {abaAtiva === 'Emendas' && <EmendasParlamentares temaClaro={temaClaro} />}
          {abaAtiva === 'Governador' && <PerfilGovernador temaClaro={temaClaro} />}
          {abaAtiva === 'Parlamentares' && <ParlamentaresGoias temaClaro={temaClaro} />}

          {/* --- ABA CONTRATOS --- */}
          {abaAtiva === 'Contratos' && dadosContratos?.kpis && !carregando && (
            <div className="animate-fade-in">
              <ContextoTela temaClaro={temaClaro} etiqueta="Compras públicas" titulo={`Auditoria de Contratos (${anoAtivo})`} descricao="Explore o volume formalizado, a quantidade de instrumentos e os fornecedores com maior valor contratado." pergunta="Quais contratos e fornecedores concentram os maiores valores registrados no período?" ressalva="Valor contratado não é sinônimo de valor pago. Vigência, aditivos, execução parcial e contratos plurianuais precisam ser consultados no documento original." />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-6 mb-8">
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>TOTAL CONTRATADO</h3><p className={`text-2xl md:text-3xl font-bold ${temaClaro ? 'text-green-600' : 'text-goiasGreen'}`}>{formatarMoeda(dadosContratos?.kpis?.valor_total)}</p></div>
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>QTD. CONTRATOS</h3><p className={`text-2xl md:text-3xl font-bold ${temaClaro ? 'text-yellow-600' : 'text-goiasYellow'}`}>{dadosContratos?.kpis?.qtd_contratos}</p></div>
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>TICKET MÉDIO</h3><p className={`text-2xl md:text-3xl font-bold ${t.destaqueValor}`}>{formatarMoeda(dadosContratos?.kpis?.ticket_medio)}</p></div>
              </div>
              
              <div className="grid grid-cols-1 gap-6">
                <div className={`border rounded-xl p-4 md:p-6 ${t.card}`}>
                  <h3 className={`text-base md:text-lg font-semibold mb-4 ${t.titulo}`}>🏆 Maiores Fornecedores</h3>
                  <div className="h-[400px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={(dadosContratos?.top_fornecedores || []).map((item) => ({ ...item, nome: formatarNomeProprio(item.nome) }))} layout="vertical" margin={{ left: 0, right: 20 }}><CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} horizontal={false} /><XAxis type="number" scale="log" domain={[10000, 'auto']} stroke={t.graficoTexto} tickFormatter={(v) => `R$ ${(v/1000000).toFixed(0)}M`}/><YAxis dataKey="nome" type="category" width={110} stroke={t.graficoTexto} fontSize={10}/><Tooltip cursor={{fill: t.graficoGrid}} contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/><Bar dataKey="valor" radius={[0, 4, 4, 0]}>{(dadosContratos?.top_fornecedores || []).map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />))}</Bar></BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* --- ABA FOLHA --- */}
          {abaAtiva === 'Folha' && dadosFolha?.kpis && !carregando && (
            <div className="animate-fade-in">
              <ContextoTela temaClaro={temaClaro} etiqueta="Pessoas e serviço público" titulo={`Folha de Pagamento (${anoAtivo})`} descricao="Observe a remuneração bruta registrada, sua distribuição institucional e os maiores valores individuais do período." pergunta="Qual é o volume da folha e em quais órgãos os registros se concentram?" ressalva="Quantidade de registros não equivale necessariamente a servidores distintos. Remuneração bruta pode incluir retroativos, férias, decisões judiciais e outras verbas eventuais." />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-6 mb-8">
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>TOTAL DA FOLHA</h3><p className={`text-2xl md:text-3xl font-bold ${temaClaro ? 'text-green-600' : 'text-goiasGreen'}`}>{formatarMoeda(dadosFolha?.kpis?.total_folha)}</p></div>
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>QTD. SERVIDORES</h3><p className={`text-2xl md:text-3xl font-bold ${temaClaro ? 'text-yellow-600' : 'text-goiasYellow'}`}>{dadosFolha?.kpis?.qtd_servidores}</p></div>
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>MÉDIA SALARIAL</h3><p className={`text-2xl md:text-3xl font-bold ${t.destaqueValor}`}>{formatarMoeda(dadosFolha?.kpis?.media_salarial)}</p></div>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div className={`border rounded-xl p-4 md:p-6 ${t.card}`}>
                  <h3 className={`text-base md:text-lg font-semibold mb-4 ${t.titulo}`}>🚨 Maiores Salários</h3>
                  <div className="h-64 min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={(dadosFolha?.top_salarios || []).map((item) => ({ ...item, nome: formatarNomeProprio(item.nome) }))} layout="vertical" margin={{ left: 0, right: 20 }}><CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} horizontal={false} /><XAxis type="number" stroke={t.graficoTexto} tickFormatter={(v) => `R$ ${(v/1000).toFixed(0)}k`}/><YAxis dataKey="nome" type="category" width={110} stroke={t.graficoTexto} fontSize={10}/><Tooltip cursor={{fill: t.graficoGrid}} contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/><Bar dataKey="valor" radius={[0, 4, 4, 0]}>{(dadosFolha?.top_salarios || []).map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />))}</Bar></BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className={`border rounded-xl p-4 md:p-6 ${t.card}`}>
                  <h3 className={`text-base md:text-lg font-semibold mb-4 ${t.titulo}`}>🏛️ Gastos por Órgão</h3>
                  <div className="h-64 min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart><Pie data={(dadosFolha?.distribuicao || []).map((e) => ({ ...e, name: formatarNomeProprio(e.name) }))} outerRadius={80} dataKey="value" label={({name}) => name.substring(0, 10) + ".."} fill={t.graficoTexto}>{(dadosFolha?.distribuicao || []).map((e, i) => (<Cell key={i} fill={CORES_GRAFICOS[i % CORES_GRAFICOS.length]} />))}</Pie><Tooltip contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/></PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Registros priorizados por regra determinística para revisão humana. */}
              {dadosFolha?.alertas_ia && dadosFolha.alertas_ia.length > 0 && (
                <div className={`border rounded-xl p-6 shadow-lg mt-6 ${temaClaro ? 'bg-red-50 border-red-200' : 'bg-darkCard border-red-900/50 shadow-[0_0_15px_rgba(239,68,68,0.1)]'}`}>
                  <h3 className={`text-xl font-bold mb-4 flex items-center gap-2 ${temaClaro ? 'text-red-700' : 'text-red-400'}`}>
                    Registros para contextualização
                  </h3>
                  <p className={`text-sm mb-4 ${temaClaro ? 'text-red-600' : 'text-gray-400'}`}>
                    Maiores remunerações brutas individuais do período. A posição no ranking não indica irregularidade e pode refletir pagamentos acumulados, decisões judiciais ou outras situações funcionais.
                  </p>
                  <div className="space-y-3">
                    {dadosFolha.alertas_ia.map((alerta, index) => (
                      <div key={index} className={`p-4 rounded-lg border-l-4 flex flex-col sm:flex-row justify-between sm:items-center gap-2 ${temaClaro ? 'bg-white border-red-500 shadow-sm' : 'bg-red-900/10 border-red-500'}`}>
                        <div>
                          <p className={`font-bold ${t.titulo}`}>{formatarNomeProprio(alerta.nome)}</p>
                          <p className={`text-xs ${t.subtitulo}`}>{formatarNomeProprio(alerta.orgao)}</p>
                        </div>
                        <div className="text-left sm:text-right">
                          <p className={`text-lg font-bold ${temaClaro ? 'text-red-600' : 'text-red-400'}`}>{formatarMoeda(alerta.valor)}</p>
                          <span className={`text-[10px] px-2 py-1 rounded-full uppercase tracking-wider ${temaClaro ? 'bg-red-100 text-red-700' : 'bg-red-900/40 text-red-300'}`}>
                            {alerta.motivo}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* --- ABA DIÁRIAS --- */}
          {abaAtiva === 'Diárias' && dadosDiarias?.kpis && !carregando && (
            <div className="animate-fade-in">
              <ContextoTela temaClaro={temaClaro} etiqueta="Deslocamentos a serviço" titulo={`Diárias e Passagens (${anoAtivo})`} descricao="Acompanhe os valores registrados para viagens, pessoas com maior soma e destinos mais frequentes em valor." pergunta="Quanto foi registrado em deslocamentos e onde estão os maiores volumes acumulados?" ressalva="Valor elevado pode resultar de várias viagens, distância, duração ou missão específica. O ranking orienta a consulta do motivo e dos documentos; não determina irregularidade." />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-6 mb-8">
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>TOTAL GASTO</h3><p className={`text-2xl md:text-3xl font-bold ${temaClaro ? 'text-green-600' : 'text-goiasGreen'}`}>{formatarMoeda(dadosDiarias?.kpis?.total_gasto)}</p></div>
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>QTD. VIAGENS</h3><p className={`text-2xl md:text-3xl font-bold ${temaClaro ? 'text-yellow-600' : 'text-goiasYellow'}`}>{dadosDiarias?.kpis?.qtd_viagens}</p></div>
                <div className={`border rounded-xl p-5 md:p-6 ${t.card}`}><h3 className={`text-xs md:text-sm font-semibold mb-1 ${t.subtitulo}`}>MAIOR DIÁRIA</h3><p className={`text-2xl md:text-3xl font-bold ${t.destaqueValor}`}>{formatarMoeda(dadosDiarias?.kpis?.maior_diaria)}</p></div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div className={`border rounded-xl p-4 md:p-6 ${t.card}`}>
                  <h3 className={`text-base md:text-lg font-semibold mb-4 ${t.titulo}`}>✈️ Top Viajantes</h3>
                  <div className="h-64 min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={(dadosDiarias?.top_viajantes || []).map((item) => ({ ...item, nome: formatarNomeProprio(item.nome) }))} layout="vertical" margin={{ left: 0, right: 20 }}><CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} horizontal={false} /><XAxis type="number" stroke={t.graficoTexto} tickFormatter={(v) => `R$ ${(v/1000).toFixed(0)}k`}/><YAxis dataKey="nome" type="category" width={110} stroke={t.graficoTexto} fontSize={10}/><Tooltip cursor={{fill: t.graficoGrid}} contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/><Bar dataKey="valor" radius={[0, 4, 4, 0]}>{(dadosDiarias?.top_viajantes || []).map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />))}</Bar></BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className={`border rounded-xl p-4 md:p-6 ${t.card}`}>
                  <h3 className={`text-base md:text-lg font-semibold mb-4 ${t.titulo}`}>📍 Top Destinos</h3>
                  <div className="h-64 min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart><Pie data={(dadosDiarias?.top_destinos || []).map((e) => ({ ...e, name: formatarNomeProprio(e.name) }))} outerRadius={80} dataKey="value" label={({name}) => name.substring(0, 10) + ".."} fill={t.graficoTexto}>{(dadosDiarias?.top_destinos || []).map((e, i) => (<Cell key={i} fill={CORES_GRAFICOS[i % CORES_GRAFICOS.length]} />))}</Pie><Tooltip contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/></PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

export default App;
