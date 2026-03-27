import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid } from 'recharts';
import { LayoutDashboard, FileText, Plane, Users, Loader2, Sun, Moon } from 'lucide-react';

const CORES_GRAFICOS = ['#00D4FF', '#8A2BE2', '#FF007F', '#00FA9A', '#FFA500'];
const formatarMoeda = (valor) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor || 0);

function App() {
  const [abaAtiva, setAbaAtiva] = useState('Visão Geral');
  const [carregando, setCarregando] = useState(false);
  const [anoAtivo, setAnoAtivo] = useState('todos'); 
  const [temaClaro, setTemaClaro] = useState(false);

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
  };

  useEffect(() => {
    let isMounted = true; 
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 15000);

    const buscarDados = async () => {
      let url = "";
      let setDadosAtuais = null;

      if (abaAtiva === 'Visão Geral' && !dadosGerais) { 
        url = `http://localhost:8000/api/geral/resumo?ano=${anoAtivo}`; 
        setDadosAtuais = setDadosGerais; 
      }
      else if (abaAtiva === 'Contratos' && !dadosContratos) { 
        url = `http://localhost:8000/api/contratos/resumo?ano=${anoAtivo}`; 
        setDadosAtuais = setDadosContratos; 
      }
      else if (abaAtiva === 'Folha' && !dadosFolha) { 
        url = `http://localhost:8000/api/folha/resumo?ano=${anoAtivo}`; 
        setDadosAtuais = setDadosFolha; 
      }
      else if (abaAtiva === 'Diárias' && !dadosDiarias) { 
        url = `http://localhost:8000/api/diarias/resumo?ano=${anoAtivo}`; 
        setDadosAtuais = setDadosDiarias; 
      }

      if (url && setDadosAtuais) {
        setCarregando(true);
        try {
          const resposta = await fetch(url, { signal: abortController.signal });
          clearTimeout(timeoutId); 
          
          if (!resposta.ok) throw new Error("Erro interno do servidor Python");
          
          const dados = await resposta.json();
          if (isMounted) setDadosAtuais(dados);

        } catch (erro) {
          if (!isMounted) return; 
          console.error("🚨 Falha na Busca:", erro);
          if (erro.name === 'AbortError') {
            setDadosAtuais({ erro: "⏳ O Servidor demorou muito a responder (Timeout de 15s)." });
          } else {
            setDadosAtuais({ erro: "🔌 Falha de conexão. O servidor Python está ligado?" });
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

  // DICIONÁRIO DE ESTILOS DO TEMA CLARO / ESCURO
  const t = {
    fundoBase: temaClaro ? "bg-gray-50 text-gray-800" : "bg-darkBg text-gray-200",
    menuLateral: temaClaro ? "bg-white border-gray-200" : "bg-darkBg border-darkBorder",
    card: temaClaro ? "bg-white border-gray-200 shadow-md" : "bg-darkCard border-darkBorder shadow-lg",
    titulo: temaClaro ? "text-gray-900" : "text-white",
    subtitulo: temaClaro ? "text-gray-500" : "text-gray-400",
    destaqueValor: temaClaro ? "text-gray-800" : "text-gray-100",
    seletorAno: temaClaro ? "bg-gray-100 text-gray-800 border-gray-300" : "bg-darkCard text-white border-darkBorder",
    graficoGrid: temaClaro ? "#E5E7EB" : "#2E323E",
    graficoTexto: temaClaro ? "#6B7280" : "#9CA3AF",
    tooltipBg: temaClaro ? "#FFFFFF" : "#1A1C23",
    tooltipBorder: temaClaro ? "#E5E7EB" : "#2E323E",
    tooltipTexto: temaClaro ? "#1F2937" : "#FFFFFF"
  };

  const cssBotao = (nome) => `flex items-center gap-3 w-full px-4 py-3 rounded-lg transition-colors text-left ${
    abaAtiva === nome 
      ? (temaClaro ? "bg-green-100 text-green-700 border border-green-300 font-medium" : "bg-goiasGreen/10 text-goiasGreen border border-goiasGreen/30") 
      : (temaClaro ? "text-gray-600 hover:text-green-700 hover:bg-gray-100 border border-transparent" : "text-gray-400 hover:text-white hover:bg-darkCard border border-transparent")
  }`;

  return (
    <div className={`flex h-screen font-sans overflow-hidden transition-colors duration-300 ${t.fundoBase}`}>
      
      {/* 🔥 A MÁGICA ANTI-BORDAS: Remove as caixas de foco do Recharts! */}
      <style>{`
        .recharts-wrapper, .recharts-surface, .recharts-responsive-container, svg { outline: none !important; }
        g:focus, path:focus, rect:focus { outline: none !important; }
      `}</style>

      {/* MENU LATERAL */}
      <aside className={`w-64 border-r flex flex-col z-10 transition-colors duration-300 ${t.menuLateral}`}>
        <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Flag_of_Goi%C3%A1s.svg/1280px-Flag_of_Goi%C3%A1s.svg.png" alt="Bandeira de Goiás" className="h-6 rounded-sm shadow-sm" />
            <h1 className={`text-2xl font-bold ${temaClaro ? 'text-gray-900' : 'bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400'}`}>Radar Goiano</h1>
          </div>
          <p className={`text-xs mb-4 ${t.subtitulo}`}>Auditoria de Contas Públicas</p>

          <div className={`border rounded-lg p-1 transition-colors ${t.seletorAno}`}>
            <select 
              value={anoAtivo} 
              onChange={(e) => handleMudarAno(e.target.value)}
              className="w-full bg-transparent text-sm p-2 outline-none cursor-pointer font-medium"
            >
              <option value="todos" className={temaClaro ? "bg-white" : "bg-darkCard text-goiasYellow"}>🌟 Todos os Anos (Histórico)</option>
              {Array.from({ length: 2026 - 2013 + 1 }, (_, i) => 2026 - i).map(ano => (
                <option key={ano} value={ano.toString()} className={temaClaro ? "bg-white" : "bg-darkCard"}>
                  Exercício {ano}
                </option>
              ))}
            </select>
          </div>
        </div>        
        
        <nav className="flex-1 px-4 space-y-2">
          <button onClick={() => setAbaAtiva('Visão Geral')} className={cssBotao('Visão Geral')}><LayoutDashboard size={20} /> Visão Geral</button>
          <button onClick={() => setAbaAtiva('Contratos')} className={cssBotao('Contratos')}><FileText size={20} /> Contratos</button>
          <button onClick={() => setAbaAtiva('Diárias')} className={cssBotao('Diárias')}><Plane size={20} /> Diárias e Viagens</button>
          <button onClick={() => setAbaAtiva('Folha')} className={cssBotao('Folha')}><Users size={20} /> Folha de Pagamento</button>
        </nav>

        {/* BOTÃO MUDAR TEMA */}
        <div className="p-4 border-t border-gray-200 dark:border-darkBorder">
          <button 
            onClick={() => setTemaClaro(!temaClaro)} 
            className={`flex items-center justify-center gap-2 w-full py-2 rounded-lg transition-colors border ${
              temaClaro 
                ? "bg-gray-100 text-gray-700 hover:bg-gray-200 border-gray-300" 
                : "bg-darkCard text-gray-400 hover:text-white border-darkBorder hover:bg-gray-800"
            }`}
          >
            {temaClaro ? <Moon size={18} /> : <Sun size={18} />}
            <span className="text-sm font-medium">{temaClaro ? "Modo Escuro" : "Modo Claro"}</span>
          </button>
        </div>
      </aside>

      {/* ÁREA PRINCIPAL */}
      <main className="flex-1 overflow-y-auto p-8">

        {/* LOADING GERAL */}
        {carregando && (
          <div className="flex flex-col items-center justify-center h-64"><Loader2 className="w-12 h-12 text-goiasGreen animate-spin mb-4" /></div>
        )}

        {/* MENSAGENS DE ERRO */}
        {abaAtiva === 'Visão Geral' && dadosGerais?.erro && !carregando && (
          <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-8 max-w-2xl mx-auto mt-20 text-center shadow-lg"><h3 className="text-red-400 text-2xl font-bold mb-4">⚠️ Atenção</h3><p className="text-gray-300 text-lg">{dadosGerais.erro}</p></div>
        )}
        {abaAtiva === 'Contratos' && dadosContratos?.erro && !carregando && (
          <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-8 max-w-2xl mx-auto mt-20 text-center shadow-lg"><h3 className="text-red-400 text-2xl font-bold mb-4">⚠️ Atenção</h3><p className="text-gray-300 text-lg">{dadosContratos.erro}</p></div>
        )}
        {abaAtiva === 'Folha' && dadosFolha?.erro && !carregando && (
          <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-8 max-w-2xl mx-auto mt-20 text-center shadow-lg"><h3 className="text-red-400 text-2xl font-bold mb-4">⚠️ Atenção</h3><p className="text-gray-300 text-lg">{dadosFolha.erro}</p></div>
        )}
        {abaAtiva === 'Diárias' && dadosDiarias?.erro && !carregando && (
          <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-8 max-w-2xl mx-auto mt-20 text-center shadow-lg"><h3 className="text-red-400 text-2xl font-bold mb-4">⚠️ Atenção</h3><p className="text-gray-300 text-lg">{dadosDiarias.erro}</p></div>
        )}

        {/* --- ABA VISÃO GERAL --- */}
        {abaAtiva === 'Visão Geral' && dadosGerais?.kpis && !carregando && (
          <div className="animate-fade-in">
            <div className="flex justify-between items-center mb-8">
              <h2 className={`text-3xl font-bold ${t.titulo}`}>Raio-X do Estado ({anoAtivo})</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className={`border rounded-xl p-5 ${t.card}`}><h3 className={`text-xs mb-1 font-semibold ${t.subtitulo}`}>CUSTO TOTAL AUDITADO</h3><p className={`text-2xl font-bold ${temaClaro ? 'text-green-600' : 'text-goiasGreen'}`}>{formatarMoeda(dadosGerais?.kpis?.custo_total)}</p></div>
              <div className={`border rounded-xl p-5 ${t.card}`}><h3 className={`text-xs mb-1 font-semibold ${t.subtitulo}`}>ÓRGÃO MAIS CUSTOSO</h3><p className={`text-xl font-bold whitespace-nowrap overflow-hidden text-ellipsis ${temaClaro ? 'text-yellow-600' : 'text-goiasYellow'}`} title={dadosGerais?.kpis?.orgao_campeao}>{dadosGerais?.kpis?.orgao_campeao?.substring(0, 20) || 'N/A'}...</p></div>
              <div className={`border rounded-xl p-5 ${t.card}`}><h3 className={`text-xs mb-1 font-semibold ${t.subtitulo}`}>MAIOR DESPESA ÚNICA</h3><p className={`text-2xl font-bold ${t.destaqueValor}`}>{formatarMoeda(dadosGerais?.kpis?.maior_despesa)}</p></div>
              <div className={`border rounded-xl p-5 ${temaClaro ? 'bg-red-50 border-red-200 shadow-md' : 'bg-darkCard border-red-900/50 shadow-lg'}`}><h3 className={`text-xs mb-1 font-semibold ${temaClaro ? 'text-red-700' : 'text-red-400'}`}>ALERTA TETO SALARIAL</h3><p className="text-2xl font-bold text-red-500">{dadosGerais?.kpis?.alerta_teto || 0} Servidores</p></div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <div className={`border rounded-xl p-6 ${t.card}`}>
                <h3 className={`text-lg font-semibold mb-4 ${t.titulo}`}>🍰 Distribuição do Orçamento</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart><Pie data={dadosGerais?.raio_x || []} innerRadius={60} outerRadius={90} paddingAngle={5} dataKey="value" label={({name}) => name} fill={t.graficoTexto}>{(dadosGerais?.raio_x || []).map((e, i) => <Cell key={i} fill={CORES_GRAFICOS[i % CORES_GRAFICOS.length]} />)}</Pie><Tooltip contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/></PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className={`border rounded-xl p-6 ${t.card}`}>
                <h3 className={`text-lg font-semibold mb-4 ${t.titulo}`}>🏛️ Top 5 Órgãos (Folha + Diárias)</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dadosGerais?.top_orgaos || []} layout="vertical" margin={{ left: 10, right: 30 }}><CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} horizontal={false} /><XAxis type="number" stroke={t.graficoTexto} tickFormatter={(v) => `R$ ${(v/1000000).toFixed(0)}M`}/><YAxis dataKey="nome" type="category" width={180} stroke={t.graficoTexto} fontSize={10}/><Tooltip cursor={{fill: t.graficoGrid}} contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/><Bar dataKey="total" radius={[0, 4, 4, 0]}>{(dadosGerais?.top_orgaos || []).map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />))}</Bar></BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <h3 className={`text-xl font-bold mb-4 ${t.titulo}`}>Radar de Destaques</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className={`border rounded-xl p-6 flex items-center gap-4 border-l-4 ${t.card} ${temaClaro ? 'border-l-cyan-600' : 'border-l-cyan-500'}`}>
                <div className={`p-3 rounded-full ${temaClaro ? 'bg-cyan-100 text-cyan-600' : 'bg-cyan-900/30 text-cyan-400'}`}><Plane size={30} /></div>
                <div>
                  <h4 className={`text-sm font-semibold ${t.subtitulo}`}>O MAIOR VIAJANTE</h4>
                  <p className={`text-xl font-bold ${t.titulo}`}>{dadosGerais?.anomalias?.maior_viajante?.nome || 'N/A'}</p>
                  <p className={`font-semibold ${temaClaro ? 'text-cyan-600' : 'text-cyan-400'}`}>{formatarMoeda(dadosGerais?.anomalias?.maior_viajante?.valor || 0)} <span className="text-gray-500 text-sm font-normal">em diárias</span></p>
                </div>
              </div>
              <div className={`border rounded-xl p-6 flex items-center gap-4 border-l-4 ${t.card} ${temaClaro ? 'border-l-purple-600' : 'border-l-purple-500'}`}>
                <div className={`p-3 rounded-full ${temaClaro ? 'bg-purple-100 text-purple-600' : 'bg-purple-900/30 text-purple-400'}`}><FileText size={30} /></div>
                <div>
                  <h4 className={`text-sm font-semibold ${t.subtitulo}`}>A EMPRESA FAVORITA</h4>
                  <p className={`text-xl font-bold ${t.titulo}`}>{dadosGerais?.anomalias?.empresa_favorita?.nome || 'N/A'}</p>
                  <p className={`font-semibold ${temaClaro ? 'text-purple-600' : 'text-purple-400'}`}>{dadosGerais?.anomalias?.empresa_favorita?.qtd || dadosGerais?.anomalias?.empresa_favorita?.quantidade || 0} <span className="text-gray-500 text-sm font-normal">contratos fechados</span></p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* --- ABA CONTRATOS --- */}
        {abaAtiva === 'Contratos' && dadosContratos && !dadosContratos.erro && !carregando && (
          <div className="animate-fade-in">
            <h2 className={`text-3xl font-bold mb-8 ${t.titulo}`}>Auditoria de Contratos ({anoAtivo})</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>TOTAL CONTRATADO</h3><p className={`text-3xl font-bold ${temaClaro ? 'text-green-600' : 'text-goiasGreen'}`}>{formatarMoeda(dadosContratos.kpis.valor_total)}</p></div>
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>QTD. CONTRATOS</h3><p className={`text-3xl font-bold ${temaClaro ? 'text-yellow-600' : 'text-goiasYellow'}`}>{dadosContratos.kpis.qtd_contratos}</p></div>
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>TICKET MÉDIO</h3><p className={`text-3xl font-bold ${t.destaqueValor}`}>{formatarMoeda(dadosContratos.kpis.ticket_medio)}</p></div>
            </div>
            
            <div className="grid grid-cols-1 gap-6">
              <div className={`border rounded-xl p-6 ${t.card}`}>
                <h3 className={`text-lg font-semibold mb-4 ${t.titulo}`}>🏆 Maiores Fornecedores</h3>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dadosContratos.top_fornecedores} layout="vertical" margin={{ left: 10, right: 30 }}><CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} horizontal={false} /><XAxis type="number" scale="log" domain={[10000, 'auto']} stroke={t.graficoTexto} tickFormatter={(v) => `R$ ${(v/1000000).toFixed(0)}M`}/><YAxis dataKey="nome" type="category" width={180} stroke={t.graficoTexto} fontSize={10}/><Tooltip cursor={{fill: t.graficoGrid}} contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/><Bar dataKey="valor" radius={[0, 4, 4, 0]}>{dadosContratos.top_fornecedores.map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />))}</Bar></BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* --- ABA FOLHA --- */}
        {abaAtiva === 'Folha' && dadosFolha && !dadosFolha.erro && !carregando && (
          <div className="animate-fade-in">
            <h2 className={`text-3xl font-bold mb-8 ${t.titulo}`}>Folha de Pagamento ({anoAtivo})</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>TOTAL DA FOLHA</h3><p className={`text-3xl font-bold ${temaClaro ? 'text-green-600' : 'text-goiasGreen'}`}>{formatarMoeda(dadosFolha.kpis.total_folha)}</p></div>
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>QTD. SERVIDORES</h3><p className={`text-3xl font-bold ${temaClaro ? 'text-yellow-600' : 'text-goiasYellow'}`}>{dadosFolha.kpis.qtd_servidores}</p></div>
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>MÉDIA SALARIAL</h3><p className={`text-3xl font-bold ${t.destaqueValor}`}>{formatarMoeda(dadosFolha.kpis.media_salarial)}</p></div>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <div className={`border rounded-xl p-6 ${t.card}`}>
                <h3 className={`text-lg font-semibold mb-4 ${t.titulo}`}>🚨 Maiores Salários</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dadosFolha.top_salarios} layout="vertical" margin={{ left: 10, right: 30 }}><CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} horizontal={false} /><XAxis type="number" stroke={t.graficoTexto} tickFormatter={(v) => `R$ ${(v/1000).toFixed(0)}k`}/><YAxis dataKey="nome" type="category" width={180} stroke={t.graficoTexto} fontSize={10}/><Tooltip cursor={{fill: t.graficoGrid}} contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/><Bar dataKey="valor" radius={[0, 4, 4, 0]}>{dadosFolha.top_salarios.map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />))}</Bar></BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className={`border rounded-xl p-6 ${t.card}`}>
                <h3 className={`text-lg font-semibold mb-4 ${t.titulo}`}>🏛️ Gastos por Órgão</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart><Pie data={dadosFolha.distribuicao} outerRadius={90} dataKey="value" label={({name}) => name.substring(0, 15) + "..."} fill={t.graficoTexto}>{dadosFolha.distribuicao.map((e, i) => (<Cell key={i} fill={CORES_GRAFICOS[i % CORES_GRAFICOS.length]} />))}</Pie><Tooltip contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/></PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* --- ABA DIÁRIAS --- */}
        {abaAtiva === 'Diárias' && dadosDiarias && !dadosDiarias.erro && !carregando && (
          <div className="animate-fade-in">
            <h2 className={`text-3xl font-bold mb-8 ${t.titulo}`}>Diárias e Passagens ({anoAtivo})</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>TOTAL GASTO</h3><p className={`text-3xl font-bold ${temaClaro ? 'text-green-600' : 'text-goiasGreen'}`}>{formatarMoeda(dadosDiarias.kpis.total_gasto)}</p></div>
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>QTD. VIAGENS</h3><p className={`text-3xl font-bold ${temaClaro ? 'text-yellow-600' : 'text-goiasYellow'}`}>{dadosDiarias.kpis.qtd_viagens}</p></div>
              <div className={`border rounded-xl p-6 ${t.card}`}><h3 className={`text-sm font-semibold mb-1 ${t.subtitulo}`}>MAIOR DIÁRIA</h3><p className={`text-3xl font-bold ${t.destaqueValor}`}>{formatarMoeda(dadosDiarias.kpis.maior_diaria)}</p></div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <div className={`border rounded-xl p-6 ${t.card}`}>
                <h3 className={`text-lg font-semibold mb-4 ${t.titulo}`}>✈️ Top Viajantes</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dadosDiarias.top_viajantes} layout="vertical" margin={{ left: 10, right: 30 }}><CartesianGrid strokeDasharray="3 3" stroke={t.graficoGrid} horizontal={false} /><XAxis type="number" stroke={t.graficoTexto} tickFormatter={(v) => `R$ ${(v/1000).toFixed(0)}k`}/><YAxis dataKey="nome" type="category" width={180} stroke={t.graficoTexto} fontSize={10}/><Tooltip cursor={{fill: t.graficoGrid}} contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/><Bar dataKey="valor" radius={[0, 4, 4, 0]}>{dadosDiarias.top_viajantes.map((entry, index) => (<Cell key={`cell-${index}`} fill={CORES_GRAFICOS[index % CORES_GRAFICOS.length]} />))}</Bar></BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className={`border rounded-xl p-6 ${t.card}`}>
                <h3 className={`text-lg font-semibold mb-4 ${t.titulo}`}>📍 Top Destinos</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart><Pie data={dadosDiarias.top_destinos} outerRadius={90} dataKey="value" label={({name}) => name} fill={t.graficoTexto}>{dadosDiarias.top_destinos.map((e, i) => (<Cell key={i} fill={CORES_GRAFICOS[i % CORES_GRAFICOS.length]} />))}</Pie><Tooltip contentStyle={{ backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder, color: t.tooltipTexto }} itemStyle={{ color: t.tooltipTexto }} formatter={formatarMoeda}/></PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;