import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    // Isso diz ao Cypress qual Ã© o link padrÃ£o do seu site rodando no Vite
    baseUrl: 'http://localhost:5173',
    setupNodeEvents() {
      // Aqui vocÃª pode adicionar plugins no futuro, se precisar
    },
  },
});
