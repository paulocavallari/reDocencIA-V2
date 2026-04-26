import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BookOpen, Clock3, Sparkles, Wand2 } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";

function PlansSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="h-24 animate-pulse rounded-2xl bg-secondary" />
      ))}
    </div>
  );
}

export default function HomePage() {
  const { user } = useAuth();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    api
      .get("/api/plans")
      .then(({ data }) => {
        if (!active) {
          return;
        }
        setPlans(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (active) {
          setPlans([]);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const orderedPlans = useMemo(() => [...plans].sort((left, right) => Number(right.id) - Number(left.id)), [plans]);
  const latestPlan = orderedPlans[0] || null;
  const recentPlans = orderedPlans.slice(0, 3);
  const disciplinesCount = new Set(orderedPlans.map((plan) => plan.disciplina).filter(Boolean)).size;
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) {
      return "Bom dia";
    }
    if (hour < 18) {
      return "Boa tarde";
    }
    return "Boa noite";
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 pb-10 pt-6 sm:px-6">
      {/* Hero */}
      <section className="space-y-2">
        <h1 className="text-[34px] font-bold tracking-tight text-foreground">
          {greeting}{user?.nome ? `, ${user.nome}` : ""}.
        </h1>
        <p className="max-w-xl text-[17px] leading-7 text-muted-foreground">
          O planejamento de hoje começa com menos ruído e mais direção.
        </p>
      </section>

      {/* Quick actions */}
      <section className="flex flex-wrap gap-3">
        <Button asChild size="lg">
          <Link to="/gerador">
            <Sparkles className="h-4 w-4" />
            Criar novo plano
          </Link>
        </Button>
        <Button asChild variant="secondary" size="lg">
          <Link to={latestPlan ? `/editor/${latestPlan.id}` : "/planos"}>
            {latestPlan ? "Continuar último plano" : "Abrir biblioteca"}
          </Link>
        </Button>
        {user?.is_admin ? (
          <Button asChild variant="outline" size="lg">
            <Link to="/admin">Administração</Link>
          </Button>
        ) : null}
      </section>

      {/* Stats */}
      <section className="grid gap-3 sm:grid-cols-3">
        {loading ? (
          <PlansSkeleton />
        ) : (
          <>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2 text-[12px] uppercase tracking-[0.1em]">
                  <BookOpen className="h-3.5 w-3.5" />
                  Planos criados
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-[40px] font-bold tracking-tight text-foreground">{orderedPlans.length}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2 text-[12px] uppercase tracking-[0.1em]">
                  <Clock3 className="h-3.5 w-3.5" />
                  Último plano
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="line-clamp-2 text-[20px] font-semibold text-foreground">{latestPlan?.titulo || "Nenhum"}</p>
                <p className="mt-1 text-[13px] text-muted-foreground">{latestPlan ? `${latestPlan.disciplina} · ${latestPlan.ano_serie}` : "Crie seu primeiro plano."}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2 text-[12px] uppercase tracking-[0.1em]">
                  <Wand2 className="h-3.5 w-3.5" />
                  Disciplinas
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-[40px] font-bold tracking-tight text-foreground">{disciplinesCount}</p>
              </CardContent>
            </Card>
          </>
        )}
      </section>

      {/* Recent plans */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[22px] font-semibold tracking-tight text-foreground">Planos recentes</h2>
          <Button asChild variant="ghost" size="sm" className="text-primary">
            <Link to="/planos">Ver todos</Link>
          </Button>
        </div>

        {loading ? (
          <PlansSkeleton />
        ) : recentPlans.length ? (
          <div className="space-y-2">
            {recentPlans.map((plan) => (
              <Link
                key={plan.id}
                to={`/editor/${plan.id}`}
                className="flex items-center justify-between gap-4 rounded-2xl bg-card p-4 shadow-card transition-all duration-200 hover:shadow-elevated active:scale-[0.99]"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{plan.disciplina}</Badge>
                    <span className="text-[12px] text-muted-foreground">{plan.ano_serie} · {plan.bimestre}º bim</span>
                  </div>
                  <p className="mt-1.5 truncate text-[17px] font-semibold text-foreground">{plan.titulo}</p>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </Link>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-start gap-3 p-6">
              <p className="text-[17px] font-semibold text-foreground">Nenhum plano salvo.</p>
              <p className="text-[15px] text-muted-foreground">Comece pelo gerador para criar o primeiro rascunho.</p>
              <Button asChild className="mt-1">
                <Link to="/gerador">Criar primeiro plano</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </section>

      {/* Tips */}
      <section className="space-y-3">
        <h2 className="text-[22px] font-semibold tracking-tight text-foreground">Dicas rápidas</h2>
        <div className="space-y-1">
          {[
            {
              title: "Especifique a intenção didática",
              text: "Inclua recomposição, experimentação, inclusão, tempo disponível ou restrições reais da turma.",
            },
            {
              title: "Selecione poucos conteúdos por vez",
              text: "Menos escopo gera propostas mais consistentes e reduz retrabalho depois.",
            },
            {
              title: "Revise habilidades antes de salvar",
              text: "O vínculo entre conteúdo e habilidade mantém o plano fiel ao recorte curricular.",
            },
          ].map((item) => (
            <details key={item.title} className="group rounded-2xl bg-card p-4 shadow-card">
              <summary className="cursor-pointer list-none text-[15px] font-medium text-foreground">{item.title}</summary>
              <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">{item.text}</p>
            </details>
          ))}
        </div>
      </section>
    </main>
  );
}
