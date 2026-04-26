import { useEffect, useMemo, useState } from "react";
import { BookText, FileDown, FileText, Loader2, Save, Settings2 } from "lucide-react";
import ReactQuill from "react-quill";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "../components/ui/sheet";
import api, { downloadPlanFile } from "../services/api";

const toolbar = [
  [{ font: [] }, { size: ["small", false, "large", "huge"] }],
  ["bold", "italic", "underline"],
  [{ align: [] }],
  [{ list: "ordered" }, { list: "bullet" }],
  ["clean"],
];

export default function PlanEditorPage() {
  const navigate = useNavigate();
  const { planId } = useParams();
  const [title, setTitle] = useState("Plano de Aula");
  const [html, setHtml] = useState("");
  const [metadata, setMetadata] = useState(null);
  const [skills, setSkills] = useState([]);
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState(planId || null);
  const [loading, setLoading] = useState(true);
  const [lastSavedSnapshot, setLastSavedSnapshot] = useState("");

  useEffect(() => {
    let active = true;
    if (planId) {
      api.get(`/api/plans/${planId}`).then(({ data }) => {
        if (!active) return;
        const meta = { disciplina: data.disciplina, ano_serie: data.ano_serie, nivel_ensino: data.nivel_ensino, bimestre: data.bimestre, conteudos: data.conteudos.split("\n").filter(Boolean), duracao: data.duracao, orientacoes: data.orientacoes };
        const sk = data.habilidades.split("\n").map((item, i) => ({ id: i + 1, label: item }));
        setSavedId(String(data.id)); setTitle(data.titulo); setHtml(data.plano_html); setMetadata(meta); setSkills(sk);
        setLastSavedSnapshot(JSON.stringify({ title: data.titulo, html: data.plano_html, metadata: meta, skills: sk }));
      }).finally(() => { if (active) setLoading(false); });
      return () => { active = false; };
    }
    const stored = window.sessionStorage.getItem("redocencia-draft-plan");
    if (!stored) { navigate("/gerador"); return; }
    const draft = JSON.parse(stored);
    setHtml(draft.html); setMetadata(draft.metadata); setSkills(draft.habilidades);
    setLastSavedSnapshot(JSON.stringify({ title: "Plano de Aula", html: draft.html, metadata: draft.metadata, skills: draft.habilidades }));
    setLoading(false);
    return () => { active = false; };
  }, [navigate, planId]);

  const skillLabels = skills.map((s) => s.label || `${s.habilidade_codigo}: ${s.habilidade_descricao}`);
  const currentSnapshot = useMemo(() => JSON.stringify({ title, html, metadata, skills }), [html, metadata, skills, title]);
  const hasUnsavedChanges = Boolean(metadata) && currentSnapshot !== lastSavedSnapshot;

  async function handleSave() {
    if (!metadata) return;
    const payload = { titulo: title, disciplina: metadata.disciplina, ano_serie: metadata.ano_serie, nivel_ensino: metadata.nivel_ensino, bimestre: Number(metadata.bimestre), conteudos: metadata.conteudos, habilidades: skills.map((s) => s.label || `${s.habilidade_codigo}: ${s.habilidade_descricao}`), duracao: metadata.duracao, orientacoes: metadata.orientacoes, plano_html: html };
    setSaving(true);
    try {
      const { data } = await (savedId ? api.put(`/api/plans/${savedId}`, payload) : api.post("/api/plans", payload));
      setSavedId(String(data.id));
      setLastSavedSnapshot(JSON.stringify({ title, html, metadata, skills }));
      toast.success("Plano salvo.");
    } catch { toast.error("Não foi possível salvar."); }
    finally { setSaving(false); }
  }

  function handleExport(format) {
    if (!savedId) { toast.error("Salve antes de exportar."); return; }
    downloadPlanFile(savedId, format, title).catch(() => toast.error(`Erro ao exportar ${format.toUpperCase()}.`));
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 pb-10 pt-6 sm:px-6">
      {/* Toolbar */}
      <div className="sticky top-14 z-20 -mx-4 border-b border-border/40 bg-white/80 px-4 py-3 backdrop-blur-2xl backdrop-saturate-150 sm:-mx-6 sm:px-6">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0 flex-1">
            <div className="mb-1.5 flex items-center gap-2">
              {hasUnsavedChanges ? (
                <span className="inline-flex items-center gap-1 text-[12px] font-medium text-[hsl(var(--success))]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--success))]" />
                  Alterações não salvas
                </span>
              ) : (
                <span className="text-[12px] text-muted-foreground">Salvo</span>
              )}
            </div>
            <input
              className="w-full border-0 bg-transparent p-0 text-[28px] font-bold tracking-tight text-foreground outline-none placeholder:text-muted-foreground/40"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Título do plano"
            />
            {metadata ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge>{metadata.disciplina}</Badge>
                <Badge variant="outline">{metadata.ano_serie}</Badge>
                <Badge variant="outline">{metadata.duracao}</Badge>
                <Badge variant="outline">{metadata.bimestre}º bim</Badge>
              </div>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => handleExport("pdf")}>
              <FileDown className="h-4 w-4" /> PDF
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => handleExport("docx")}>
              <FileText className="h-4 w-4" /> DOCX
            </Button>
            <Sheet>
              <SheetTrigger asChild>
                <Button type="button" variant="ghost" size="sm">
                  <Settings2 className="h-4 w-4" /> Info
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="max-w-md">
                <SheetHeader>
                  <SheetTitle>Metadados do plano</SheetTitle>
                  <SheetDescription>Recorte curricular e habilidades vinculadas.</SheetDescription>
                </SheetHeader>
                {metadata ? (
                  <div className="mt-5 grid gap-4">
                    <div className="rounded-xl bg-secondary p-4">
                      <p className="text-[13px] font-semibold text-foreground">Dados do plano</p>
                      <div className="mt-3 grid gap-3 text-[13px]">
                        {[["Disciplina", metadata.disciplina], ["Turma", metadata.ano_serie], ["Etapa", metadata.nivel_ensino], ["Duração", metadata.duracao]].map(([l, v]) => (
                          <div key={l}><p className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground">{l}</p><p className="mt-0.5 font-medium text-foreground">{v}</p></div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-xl bg-secondary p-4">
                      <p className="text-[13px] font-semibold text-foreground">Conteúdos</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">{metadata.conteudos?.length ? metadata.conteudos.map((c) => <Badge key={c}>{c}</Badge>) : <p className="text-[13px] text-muted-foreground">Sem conteúdos.</p>}</div>
                    </div>
                    <div className="rounded-xl bg-secondary p-4">
                      <p className="text-[13px] font-semibold text-foreground">Habilidades</p>
                      <div className="mt-2 grid gap-1.5">{skillLabels.length ? skillLabels.map((s, i) => <div key={`${s}-${i}`} className="rounded-lg bg-card p-2.5 text-[13px] text-muted-foreground">{s}</div>) : <p className="text-[13px] text-muted-foreground">Nenhuma.</p>}</div>
                    </div>
                  </div>
                ) : <div className="mt-5 rounded-xl bg-secondary p-4 text-[13px] text-muted-foreground">Carregando...</div>}
              </SheetContent>
            </Sheet>
            <Button type="button" onClick={handleSave} disabled={saving || !metadata}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {saving ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        </div>
      </div>

      {/* Editor */}
      {loading ? (
        <div className="grid gap-3">
          <div className="h-16 animate-pulse rounded-2xl bg-secondary" />
          <div className="h-[60vh] animate-pulse rounded-2xl bg-secondary" />
        </div>
      ) : (
        <ReactQuill modules={{ toolbar }} theme="snow" value={html} onChange={setHtml} className="plan-editor" />
      )}
    </main>
  );
}
