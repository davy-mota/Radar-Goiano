describe('Radar Goiano - Testes de Interface e IntegraÃ§Ã£o', () => {

  beforeEach(() => {
    // O Cypress sempre vai acessar a pÃ¡gina inicial antes de cada teste
    cy.visit('/');
  });

  it('Deve carregar a pÃ¡gina inicial e exibir o tÃ­tulo do sistema', () => {
    // Verifica se o nome do projeto estÃ¡ na tela
    cy.contains('h1', 'Radar Goiano').should('be.visible');

    // Verifica se o menu carregou
    cy.contains('button', 'VisÃ£o Geral').should('be.visible');
  });

  it('Deve alternar para o Tema Claro com sucesso', () => {
    // O padrÃ£o inicial do App.jsx Ã© o tema escuro. Vamos testar o botÃ£o!
    cy.contains('button', 'Modo Claro').click();

    // O texto do botÃ£o deve mudar para "Modo Escuro"
    cy.contains('button', 'Modo Escuro').should('be.visible');

    // CORREÃ‡ÃƒO: Procura a div principal do seu layout em vez da div do React
    cy.get('.flex.h-screen').should('have.class', 'bg-gray-50');
  });

  it('Deve navegar para a aba Folha de Pagamento e renderizar os KPIs', () => {
    cy.contains('button', 'Folha de Pagamento').click();

    cy.contains('h2', 'Folha de Pagamento (todos)').should('be.visible');

    cy.contains('TOTAL DA FOLHA').should('be.visible');
    cy.contains('QTD. SERVIDORES').should('be.visible');
    cy.contains('MÃ‰DIA SALARIAL').should('be.visible');
  });

  it('CRÃTICO: Deve exibir o Alerta da InteligÃªncia Artificial na Folha', () => {
    cy.contains('button', 'Folha de Pagamento').click();

    // CORREÃ‡ÃƒO: Manda o Cypress "rolar a tela" atÃ© o alerta da IA aparecer
    cy.contains('h3', 'Malha Fina da InteligÃªncia Artificial')
      .scrollIntoView()
      .should('be.visible');

    cy.contains('O algoritmo Isolation Forest').should('be.visible');

    // Garante que pelo menos um alerta foi desenhado na tela
    cy.contains('SalÃ¡rio com desvio estatÃ­stico').should('exist');
  });

  // --- TESTE 1: ABA PADRÃƒO (VISÃƒO GERAL) ---
  it('Deve renderizar os KPIs principais na aba inicial (VisÃ£o Geral)', () => {
    // Como Ã© a aba padrÃ£o, nÃ£o precisa clicar no menu
    cy.contains('h2', 'Raio-X (todos)').should('be.visible');

    // Verifica se os cards de indicadores carregaram
    cy.contains('CUSTO TOTAL AUDITADO').should('be.visible');
    cy.contains('Ã“RGÃƒO MAIS CUSTOSO').should('be.visible');
    cy.contains('MAIOR DESPESA ÃšNICA').should('be.visible');
    cy.contains('ALERTA TETO SALARIAL').should('be.visible');
  });

  // --- TESTE 2: RADAR DE DESTAQUES (SCROLL) ---
  it('Deve exibir o Radar de Destaques na VisÃ£o Geral', () => {
    // Rola a pÃ¡gina para baixo para ver os destaques especiais
    cy.contains('h3', 'Radar de Destaques').scrollIntoView().should('be.visible');

    // Verifica se os blocos roxos e azuis da interface apareceram
    cy.contains('O MAIOR VIAJANTE').should('be.visible');
    cy.contains('A EMPRESA FAVORITA').should('be.visible');
  });

  // --- TESTE 3: ABA DE CONTRATOS ---
  it('Deve navegar para a aba Contratos e exibir seus indicadores', () => {
    cy.contains('button', 'Contratos').click();

    cy.contains('h2', 'Auditoria de Contratos (todos)').should('be.visible');

    // Confirma se os KPIs especÃ­ficos de licitaÃ§Ãµes estÃ£o na tela
    cy.contains('TOTAL CONTRATADO').should('be.visible');
    cy.contains('QTD. CONTRATOS').should('be.visible');
    cy.contains('TICKET MÃ‰DIO').should('be.visible');

    // Rola a tela e verifica se o tÃ­tulo do grÃ¡fico carregou
    cy.contains('h3', 'Maiores Fornecedores').scrollIntoView().should('be.visible');
  });

  // --- TESTE 4: ABA DE DIÃRIAS ---
  it('Deve navegar para a aba DiÃ¡rias e Viagens e exibir seus painÃ©is', () => {
    cy.contains('button', 'DiÃ¡rias e Viagens').click();

    cy.contains('h2', 'DiÃ¡rias e Passagens (todos)').should('be.visible');

    // Confirma se os KPIs de logÃ­stica carregaram
    cy.contains('TOTAL GASTO').should('be.visible');
    cy.contains('MAIOR DIÃRIA').should('be.visible');

    // Confirma se os tÃ­tulos dos grÃ¡ficos de viagens estÃ£o visÃ­veis
    cy.contains('h3', 'Top Viajantes').scrollIntoView().should('be.visible');
    cy.contains('h3', 'Top Destinos').should('be.visible');
  });

  // --- TESTE 5: INTERAÃ‡ÃƒO COM O FILTRO DE ANO ---
  it('Deve alterar o ano de exercÃ­cio no menu e atualizar os dados da tela', () => {
    // O Cypress busca o elemento <select> na tela e escolhe a opÃ§Ã£o "2026"
    cy.get('select').select('2026');

    // Verifica se o tÃ­tulo principal da pÃ¡gina atualizou dinamicamente para o ano selecionado
    cy.contains('h2', 'Raio-X (2026)').should('be.visible');

    // Testa voltar para "Todos os Anos" ("todos" Ã© o valor da tag <option>)
    cy.get('select').select('todos');
    cy.contains('h2', 'Raio-X (todos)').should('be.visible');
  });
});
