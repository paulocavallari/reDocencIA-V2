import { useEffect, useMemo, useState } from "react";
import { FileDown, FileText, Search, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "../components/ui/alert-dialog";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";
import api, { downloadPlanFile } from "../services/api";

export default function SavedPlansPage() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeDiscipline, setActiveDiscipline] = useState("Todas");

  function loadPlans() {
    setLoading(true);
    api
      .get("/api/plans")
      .then(({ data }) => setPlans(data))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadPlans();
  }, []);

  async function removePlan(planId) {
    await api.delete(`/api/plans/${planId}`);
    toast.success("Plano removido com sucesso.");
    loadPlans();
  }

  async function exportPlan(planId, format, title) {
    try {
      await downloadPlanFile(planId, format, title);
    } catch {
      toast.error(`Não foi possível exportar ${format.toUpperCase()}.`);
    }
  }

  const disciplines = useMemo(() => ["Todas", ...new Set(plans.map((plan) => plan.disciplina).filter(Boolean))], [plans]);
  const filteredPlans = useMemo(() => {
    const query = search.trim().toLowerCase();
    return plans.filter((plan) => {
      const matchesDiscipline = activeDiscipline === "Todas" || plan.disciplina === activeDiscipline;
      const matchesSearch = !query || [plan.titulo, plan.disciplina, plan.ano_serie].filter(Boolean).some((value) => String(value).toLowerCase().includes(query));
      return matchesDiscipline && matchesSearch;
    });
  }, [activeDiscipline, plans, search]);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 pb-10 pt-6 sm:px-6">
      {/* Header */}
      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-[34px] font-bold tracking-tight text-foreground">Biblioteca</h1>
            <p className="text-[15px] text-muted-foreground">
              {plans.length} {plans.length === 1 ? "plano salvo" : "planos salvos"} · {new Set(plans.map((p) => p.disciplina)).size} disciplinas
            </p>
          </div>
          <Button asChild>
            <Link to="/gerador">Novo plano</Link>
          </Button>
        </div>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/60" />
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por título, disciplina ou ano" className="pl-10" />
        </div>
      </section>

      {/* Discipline filter */}
      <div className="flex flex-wrap gap-2">
        {disciplines.map((discipline) => (
          <button
            key={discipline}
            type="button"
            onClick={() => setActiveDiscipline(discipline)}
            className={[
              "rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-all duration-200",
              activeDiscipline === discipline ? "bg-primary text-white" : "bg-secondary text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {discipline}
          </button>
        ))}
      </div>

      {/* Plans grid */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-44 animate-pulse rounded-2xl bg-secondary" />)
        ) : filteredPlans.length ? (
          filteredPlans.map((plan) => (
            <Card key={plan.id}>
              <CardContent className="flex h-full flex-col gap-4 p-5">
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-1.5">
                    <Badge>{plan.disciplina}</Badge>
                    <Badge variant="outline">{plan.ano_serie}</Badge>
                    <Badge variant="outline">{plan.bimestre}º bim</Badge>
                  </div>
                  <p className="line-clamp-2 text-[17px] font-semibold text-foreground">{plan.titulo}</p>
                </div>

                <div className="mt-auto grid grid-cols-4 gap-1.5">
                  <Button asChild variant="secondary" size="sm" className="col-span-2">
                    <Link to={`/editor/${plan.id}`}>Editar</Link>
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={() => exportPlan(plan.id, "pdf", plan.titulo)}>
                    <FileDown className="h-3.5 w-3.5" />
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button type="button" variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Excluir plano?</AlertDialogTitle>
                        <AlertDialogDescription>
                          "{plan.titulo}" será removido da sua biblioteca. Esta ação não pode ser desfeita.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogAction onClick={() => removePlan(plan.id)}>Excluir</AlertDialogAction>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card className="sm:col-span-2 lg:col-span-3">
            <CardContent className="flex flex-col items-start gap-3 p-6">
              <FileText className="h-8 w-8 text-muted-foreground" />
              <p className="text-[17px] font-semibold text-foreground">Nenhum plano encontrado.</p>
              <p className="text-[15px] text-muted-foreground">
                {plans.length ? "Ajuste a busca ou os filtros." : "Crie seu primeiro planejamento no gerador."}
              </p>
              <Button asChild className="mt-1">
                <Link to="/gerador">Ir para o gerador</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </section>
    </main>
  );
}
