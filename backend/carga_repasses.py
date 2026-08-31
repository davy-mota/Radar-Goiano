import hashlib,io,json,re
import pandas as pd, requests
from sqlalchemy import text
from database import engine
API='https://dadosabertos.go.gov.br/api/3/action/package_show'
MESES={'Janeiro':1,'Fevereiro':2,'Março':3,'Abril':4,'Maio':5,'Junho':6,'Julho':7,'Agosto':8,'Setembro':9,'Outubro':10,'Novembro':11,'Dezembro':12}
VALORES={'deducao_icms':'DEDUCAO_FUNDEB_ICMS','bruto_icms':'VALOR_BRUTO_ICMS','credito_icms':'VALOR_CREDITADO_ICMS','deducao_ipi':'DEDUCAO_FUNDEB_IPI','bruto_ipi':'VALOR_BRUTO_IPI','credito_ipi':'VALOR_CREDITADO_IPI','deducao_ipva':'DEDUCAO_FUNDEB_IPVA','bruto_ipva':'VALOR_BRUTO_IPVA','credito_ipva':'VALOR_CREDITADO_IPVA'}
def carregar(ano):
 p=requests.get(API,params={'id':'repasses'},timeout=60).json()['result']; recursos=[]
 for r in p['resources']:
  m=re.search(rf'Repasses - ({"|".join(MESES)})/{ano}',r.get('name',''))
  if m and r.get('format','').upper()=='CSV': recursos.append((MESES[m.group(1)],r))
 recursos.sort();
 if not recursos: raise RuntimeError('Nenhum recurso mensal encontrado.')
 with engine.begin() as c:lote=c.execute(text("INSERT INTO lotes_repasses(status,recursos) VALUES('preparando',CAST(:r AS jsonb)) RETURNING id"),{'r':json.dumps([{'id':r['id'],'nome':r['name'],'url':r['url']} for _,r in recursos])}).scalar_one()
 try:
  for mes,r in recursos:
   df=pd.read_csv(io.BytesIO(requests.get(r['url'],timeout=120).content),sep=';',dtype=str,encoding='utf-8',encoding_errors='replace').fillna('')
   itens=[]
   for x in df.to_dict('records'):
    if int(x['ANO_MES_REPASSE'][:4])!=ano or int(x['ANO_MES_REPASSE'][-2:])!=mes: raise ValueError('Período divergente')
    item={'lote_id':lote,'recurso_id':r['id'],'data_credito':pd.to_datetime(x['DATA_CREDITO'],format='mixed',dayfirst=True).date(),'ano':ano,'mes':mes,'municipio':x['NOME_MUNICIPIO'].strip()}
    item.update({k:float(x.get(v) or 0) for k,v in VALORES.items()});item['chave_conteudo']=hashlib.sha256(json.dumps(item,sort_keys=True,default=str).encode()).hexdigest();itens.append(item)
   cols=list(itens[0]);sql=text(f"INSERT INTO fatos_repasses_municipais({','.join(cols)}) VALUES({','.join(':'+x for x in cols)}) ON CONFLICT DO NOTHING")
   with engine.begin() as c:
    for i in range(0,len(itens),1000):c.execute(sql,itens[i:i+1000])
  with engine.begin() as c:
   m=c.execute(text("SELECT COUNT(*) registros,COUNT(DISTINCT mes) meses,SUM(credito_icms+credito_ipi+credito_ipva) creditado FROM fatos_repasses_municipais WHERE lote_id=:l"),{'l':lote}).mappings().one()
   if not m['registros'] or m['meses']!=len(recursos):raise ValueError('Cobertura inválida')
   c.execute(text("UPDATE lotes_repasses SET status='arquivado' WHERE status='ativo'"));c.execute(text("UPDATE lotes_repasses SET status='ativo',finalizado_em=now(),metricas=CAST(:m AS jsonb) WHERE id=:l"),{'l':lote,'m':json.dumps(dict(m),default=float)})
  return lote
 except Exception as e:
  with engine.begin() as c:c.execute(text("UPDATE lotes_repasses SET status='rejeitado',observacao=:e WHERE id=:l"),{'l':lote,'e':str(e)})
  raise
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--ano',type=int,required=True);a=p.parse_args();print('Lote ativo:',carregar(a.ano))
