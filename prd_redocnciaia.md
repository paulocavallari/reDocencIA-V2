# PRD - redocênciaIA

## 1. Visão Geral do Produto
O **redocênciaIA** é uma plataforma inteligente projetada para auxiliar professores e instituições de ensino na criação, organização e gestão de planos de aula de alta qualidade, utilizando Inteligência Artificial para otimizar o tempo pedagógico e garantir alinhamento curricular.

## 2. Objetivos Estratégicos
*   **Eficiência Pedagógica:** Reduzir o tempo gasto por professores em tarefas burocráticas de planejamento.
*   **Qualidade Educacional:** Utilizar IA para sugerir conteúdos e habilidades alinhados com as diretrizes curriculares.
*   **Centralização:** Oferecer um repositório único e organizado para todos os planos de aula e recursos do docente.

## 3. Público-Alvo
*   Professores da Educação Básica e Ensino Superior.
*   Coordenadores Pedagógicos.
*   Instituições de ensino que buscam padronização e inovação no planejamento.

## 4. Funcionalidades Principais (Escopo)

### 4.1. Painel de Controle (Dashboard)
*   Visão geral de métricas (Planos criados, Disciplinas vinculadas).
*   Acesso rápido às funcionalidades principais (Criar novo plano, Biblioteca).
*   Seção de "Dicas Rápidas" com boas práticas pedagógicas.
*   Lista de planos recentes para continuação rápida do trabalho.

### 4.2. Gerador de Planos (IA)
*   **Stepper de 4 etapas:** Contexto, Conteúdos, Habilidades e Instruções.
*   Formulário intuitivo para definição de Nível de Ensino, Bimestre, Ano/Série e Disciplina.
*   Integração com modelos de linguagem (via OpenRouter) para geração automatizada de sugestões.

### 4.3. Biblioteca de Planos
*   Repositório centralizado de todos os planos salvos.
*   Sistema de busca por título, disciplina ou ano.
*   Filtros rápidos para navegação eficiente.

### 4.4. Painel Administrativo
*   Gestão de chaves de API (OpenRouter).
*   Monitoramento de banco de dados (Supabase).
*   Status de importação de currículos e sincronização.

## 5. Requisitos de Experiência do Usuário (UX)
*   **Responsividade:** Design Mobile-First adaptado perfeitamente para Desktop.
*   **Clareza Visual:** Uso da fonte Lexend (especialmente desenhada para leitura) e paleta de cores Lumina Academic (focada em foco e produtividade).
*   **Consistência:** Uso de componentes compartilhados e Design System unificado.

## 6. Pilha Tecnológica (Sugerida)
*   **Frontend:** React / Tailwind CSS.
*   **Backend/Database:** Supabase.
*   **IA:** OpenRouter (acesso a modelos como GPT-4, Claude, etc.).
*   **Design Framework:** Stitch Design System (Lumina Academic).

## 7. Critérios de Sucesso
*   Redução de pelo menos 50% no tempo de criação de um plano de aula estruturado.
*   Interface intuitiva que dispense treinamento técnico para o professor.
*   Alta taxa de retenção de usuários na biblioteca pessoal.
