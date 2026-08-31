import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ContextoTela from './ContextoTela.jsx';
import { useTema } from '../theme.js';
import { formatarNomeProprio } from '../utils/formatarTexto.js';

const API=import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moeda=(v)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',notation:'compact'}).format(Number(v)||0);
export default function PoliticasPublicas({temaClaro}){
 const [anos,setAnos]=useState([]),[ano,setAno]=useState(''),[dados,setDados]=useState(null),[erro,setErro]=useState('');
 useEffect(()=>{fetch(`${API}/api/politicas/anos`).then(r=>r.json()).then(d=>{setAnos(d.anos);setAno(String(d.anos[0]||''));}).catch(()=>setErro('Não foi possível consultar os períodos.'));},[]);
 useEffect(()=>{if(!ano)return;fetch(`${API}/api/politicas/resumo?ano=${ano}`).then(r=>{if(!r.ok)throw Error();return r.json()}).then(setDados).catch(()=>setErro('Não foi possível carregar a classificação orçamentária.'));},[ano]);
 const t=useTema(temaClaro);
 return <div className="animate-fade-in"><ContextoTela temaClaro={temaClaro} etiqueta="Políticas financiadas" titulo="Para que áreas o recurso foi destinado?" descricao="Traduza a execução financeira em funções públicas e tipos de despesa." pergunta="Quanto foi pago em educação, saúde, segurança e outras funções — e com que natureza econômica?" ressalva="Classificação orçamentária descreve a finalidade administrativa do lançamento. Ela não mede, sozinha, qualidade, alcance ou resultado da política.">{anos.length>0&&<select aria-label="Ano das políticas" value={ano} onChange={e=>setAno(e.target.value)} className={`border rounded-lg p-3 ${t.campo}`}>{anos.map(a=><option key={a}>{a}</option>)}</select>}</ContextoTela>
 {erro&&<div role="alert" className="p-4 text-red-500">{erro}</div>}{!erro&&!dados&&<div className="h-56 flex items-center justify-center"><Loader2 className="animate-spin"/></div>}
 {dados&&<><div className="grid sm:grid-cols-3 gap-4 mb-6">{[['Empenhado',dados.kpis.empenhado],['Liquidado',dados.kpis.liquidado],['Pago',dados.kpis.pago]].map(([n,v])=><div className={`border rounded-xl p-5 ${t.card}`} key={n}><p className={t.subtitulo}>{n}</p><p className={`text-2xl font-black mt-2 ${t.titulo}`}>{moeda(v)}</p></div>)}</div><div className={`border rounded-2xl p-5 ${t.card}`}><h3 className={`font-black mb-2 ${t.titulo}`}>Funções com maior valor pago</h3><p className={`text-sm mb-5 ${t.subtitulo}`}>O tamanho do orçamento não mede sozinho a qualidade do serviço entregue.</p><div className="h-96"><ResponsiveContainer><BarChart data={dados.funcoes.map(x=>({...x,nome:formatarNomeProprio(x.nome)}))} layout="vertical"><CartesianGrid horizontal={false}/><XAxis type="number" tickFormatter={moeda}/><YAxis type="category" dataKey="nome" width={130} fontSize={10}/><Tooltip formatter={moeda}/><Bar dataKey="valor" fill="#00813A"/></BarChart></ResponsiveContainer></div></div></>}
 </div>;
}
