import { expect, test } from '@playwright/test';

test.describe('Radar Goiano', () => {
  test('carrega os painéis principais sem falhas de rede ou JavaScript', async ({ page }) => {
    const erros = [];
    page.on('console', (mensagem) => {
      if (mensagem.type() === 'error') erros.push(`console: ${mensagem.text()}`);
    });
    page.on('pageerror', (erro) => erros.push(`page: ${erro.message}`));
    page.on('requestfailed', (requisicao) => {
      const motivo = requisicao.failure()?.errorText;
      // Os componentes cancelam fetches deliberadamente quando são desmontados.
      if (motivo !== 'net::ERR_ABORTED') {
        erros.push(`request: ${requisicao.method()} ${requisicao.url()} — ${motivo}`);
      }
    });

    await page.goto('/?aba=Vis%C3%A3o+Geral&ano=2025');
    await expect(page.getByRole('heading', { name: 'Entenda o que os dados públicos mostram — e o que eles não mostram' })).toBeVisible();
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('Base auditada e versionada:')).toBeVisible();
    await expect(page.getByText(/não os somamos como se fossem o “gasto total do governo”/)).toBeVisible();
    await expect(page.getByText('CUSTO TOTAL AUDITADO')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Três perspectivas, três significados' })).toBeVisible();
    await expect(page.getByRole('alert')).toHaveCount(0);

    const telas = [
      ['Explorar Despesas', 'Explorador de Despesas'],
      ['Políticas Públicas', 'Para que áreas o recurso foi destinado?'],
      ['Repasses Municipais', 'Repasses aos Municípios'],
      ['Emendas Parlamentares', 'Emendas Parlamentares Estaduais'],
      ['Deputados e Senadores', 'Despesas de Parlamentares'],
      ['Comparar Órgãos', 'Comparador de Órgãos e Períodos'],
      ['Orçamento e Receita', 'Orçamento e Receita'],
      ['Central de Alertas', 'Central de Alertas Explicáveis'],
      ['Qualidade dos Dados', 'Qualidade e Proveniência dos Dados'],
      ['Contratos', 'Auditoria de Contratos (2025)'],
      ['Diárias e Viagens', 'Diárias e Passagens (2025)'],
      ['Folha de Pagamento', 'Folha de Pagamento (2025)'],
    ];

    for (const [botao, titulo] of telas) {
      await page.getByRole('button', { name: botao, exact: true }).click();
      await expect(page.getByRole('heading', { name: titulo, exact: true })).toBeVisible();
      await page.waitForLoadState('networkidle');
      await expect(page.getByRole('alert')).toHaveCount(0);
      await expect(page.getByText('Pergunta que esta tela responde:', { exact: false })).toBeVisible();
      await expect(page.getByText('Como interpretar:', { exact: false })).toBeVisible();
      if (botao === 'Repasses Municipais') {
        await expect(page.getByText('246 municípios conciliados', { exact: false })).toBeVisible();
        await expect(page.getByRole('img', { name: 'Mapa de repasses municipais por valor total' })).toBeVisible();
        await page.getByRole('button', { name: /^Goiânia:.*R\$/ }).click();
        await expect(page.getByText('5208707')).toBeVisible();
        await expect(page.getByRole('heading', { name: '1. De quais tributos veio o valor?' })).toBeVisible();
        await expect(page.getByRole('heading', { name: '2. Como os créditos evoluíram mês a mês?' })).toBeVisible();
        await expect(page.getByRole('heading', { name: '3. Como se compara a municípios de porte semelhante?' })).toBeVisible();
        await expect(page.getByText('1º de 246', { exact: true })).toBeVisible();
        await page.getByRole('button', { name: 'Por habitante' }).click();
        await expect(page.getByRole('heading', { name: 'Maior valor creditado por habitante' })).toBeVisible();
        await expect(page.getByRole('img', { name: 'Mapa de repasses municipais por habitante' })).toBeVisible();
      }
      if (botao === 'Emendas Parlamentares') {
        await expect(page.getByRole('region', { name: 'Etapas financeiras das emendas' })).toBeVisible();
        await expect(page.getByText('417')).toBeVisible();
        await expect(page.getByText(/12 valores monetários “#N\/D”/)).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Maiores registros empenhados' })).toBeVisible();
      }
      if (botao === 'Deputados e Senadores') {
        await expect(page.getByRole('region', { name: 'Cobertura dos cargos eletivos' })).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Deputados federais de Goiás' })).toBeVisible();
        await expect(page.getByText('Sinais para aprofundar a análise documental')).toBeVisible();
        await page.getByRole('button', { name: 'Deputados estaduais', exact: true }).click();
        await expect(page.getByRole('heading', { name: 'Deputados estaduais de Goiás' })).toBeVisible();
        await expect(page.getByText('Assembleia Legislativa de Goiás — Verba Indenizatória')).toBeVisible();
        await page.getByRole('button', { name: 'Senadores', exact: true }).click();
        await expect(page.getByRole('heading', { name: 'Senadores de Goiás' })).toBeVisible();
        await expect(page.getByText(/Jorge Kajuru não possui registro na CEAPS de 2025/)).toBeVisible();
        await expect(page.getByText('Amostra pequena').first()).toBeVisible();
      }
    }

    expect(erros, erros.join('\n')).toEqual([]);
  });

  test('persiste aba e exercício na URL', async ({ page }) => {
    await page.goto('/?aba=Vis%C3%A3o+Geral&ano=2025');
    await page.getByRole('button', { name: 'Contratos', exact: true }).click();
    await expect(page).toHaveURL(/aba=Contratos/);
    await expect(page).toHaveURL(/ano=2025/);
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Auditoria de Contratos (2025)' })).toBeVisible();
  });
});
