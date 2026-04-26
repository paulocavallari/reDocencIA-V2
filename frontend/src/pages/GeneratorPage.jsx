import { useEffect, useMemo, useState } from "react";
import { startTransition, useDeferredValue } from "react";
import { Check, ChevronLeft, ChevronRight, FileText, Loader2, Paperclip, Sparkles, Target } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import api from "../services/api";

// Resolved at build-time by Vite so the worker script is served as a static asset.
import pdfjsWorkerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

const DURATIONS = ["50 minutos", "100 minutos"];
const NIGHT_DURATIONS = ["45 minutos", "90 minutos"];
const SKILL_CATEGORY_LABELS = {
  habilidade_priorizada: "Habilidades Priorizadas",
  conhecimento_previo: "Conhecimentos Prévios",
  habilidade_relacionada: "Habilidades Relacionadas",
};
const SELECTABLE_SKILL_CATEGORIES = new Set(["habilidade_priorizada", "conhecimento_previo", "habilidade_relacionada"]);
const SKILL_CATEGORY_ORDER = ["habilidade_priorizada", "conhecimento_previo", "habilidade_relacionada"];
const STEP_ORDER = ["context", "contents", "skills", "extras"];

const fieldClassName =
  "h-11 w-full rounded-2xl border border-input bg-white px-4 text-sm text-foreground shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";
const TEXT_EXTENSIONS = new Set(["txt", "md", "csv", "json"]);
const PDF_CONTEXT_CHAR_LIMIT = 3500;

/** Extracts plain text from .txt / .md / .csv / .json files in the browser. */
async function extractTextFileContext(file) {
  if (!file) {
    return null;
  }

  const extension = (file.name.split(".").pop() || "").toLowerCase();
  const isTextLike = file.type.startsWith("text/") || TEXT_EXTENSIONS.has(extension);

  if (!isTextLike) {
    return null;
  }

  try {
    const rawText = await file.text();
    const compact = rawText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .join("\n");
    return compact.slice(0, 2200) || null;
  } catch {
    return null;
  }
}

/**
 * Extracts plain text from a PDF file using pdf.js entirely in the browser.
 * The extracted text is included in the prompt sent to OpenRouter.
 */
async function extractPdfText(file) {
  try {
    const pdfjsLib = await import("pdfjs-dist");
    pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerSrc;

    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    const maxPages = Math.min(pdf.numPages, 10);
    const parts = [];
    for (let pageNum = 1; pageNum <= maxPages; pageNum++) {
      const page = await pdf.getPage(pageNum);
      const textContent = await page.getTextContent();
      const pageText = textContent.items
        .map((item) => ("str" in item ? item.str : ""))
        .join(" ");
      parts.push(pageText);
    }
    const raw = parts.join("\n");
    const compact = raw
      .split(/[\n\r]+/)
      .map((l) => l.trim())
      .filter(Boolean)
      .join("\n");
    return compact.slice(0, PDF_CONTEXT_CHAR_LIMIT) || null;
  } catch {
    return null;
  }
}

function StepIndicator({ label, index, active, completed, meta, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex min-w-[170px] flex-1 items-center gap-3 rounded-[1.4rem] border px-4 py-3 text-left transition-colors",
        active ? "border-blue-200 bg-blue-50" : completed ? "border-emerald-200 bg-emerald-50/70" : "border-border bg-white/90 hover:bg-slate-50",
      ].join(" ")}
    >
      <span
        className={[
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
          completed ? "bg-emerald-600 text-white" : active ? "bg-primary text-white" : "bg-slate-100 text-slate-700",
        ].join(" ")}
      >
        {completed ? <Check className="h-4 w-4" /> : index + 1}
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-slate-900">{label}</span>
        <span className="block truncate text-xs text-muted-foreground">{meta}</span>
      </span>
    </button>
  );
}

function SectionHeading({ eyebrow, title, description }) {
  return (
    <div className="space-y-2">
      <Badge className="w-fit">{eyebrow}</Badge>
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-950">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

export default function GeneratorPage() {
  const navigate = useNavigate();
  const [levels, setLevels] = useState([]);
  const [years, setYears] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [aes, setAes] = useState([]);
  const [contents, setContents] = useState([]);
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [activeStep, setActiveStep] = useState("context");
  const [form, setForm] = useState({
    nivel_ensino: "",
    bimestre: "",
    ano_serie: "",
    disciplina: "",
    ae_id: "",
    conteudos: [],
    habilidades_ids: [],
    objetivos: "",
    duracao: "50 minutos",
    orientacoes: "",
  });

  const deferredContents = useDeferredValue(form.conteudos);

  useEffect(() => {
    api.get("/api/curriculum/niveis").then(({ data }) => setLevels(data));
  }, []);

  useEffect(() => {
    if (!form.nivel_ensino || !form.bimestre) {
      setYears([]);
      return;
    }
    api
      .get("/api/curriculum/anos", { params: { nivel: form.nivel_ensino, bimestre: Number(form.bimestre) } })
      .then(({ data }) => setYears(data));
  }, [form.nivel_ensino, form.bimestre]);

  useEffect(() => {
    if (!form.nivel_ensino || !form.bimestre || !form.ano_serie) {
      setSubjects([]);
      return;
    }
    api
      .get("/api/curriculum/disciplinas", {
        params: { nivel: form.nivel_ensino, bimestre: Number(form.bimestre), ano: form.ano_serie },
      })
      .then(({ data }) => setSubjects(data));
  }, [form.nivel_ensino, form.bimestre, form.ano_serie]);

  useEffect(() => {
    if (!form.nivel_ensino || !form.bimestre || !form.ano_serie || !form.disciplina) {
      setAes([]);
      return;
    }

    api
      .get("/api/curriculum/aes", {
        params: {
          nivel: form.nivel_ensino,
          bimestre: Number(form.bimestre),
          ano: form.ano_serie,
          disciplina: form.disciplina,
        },
      })
      .then(({ data }) => setAes(data));
  }, [form.nivel_ensino, form.bimestre, form.ano_serie, form.disciplina]);

  useEffect(() => {
    if (!form.nivel_ensino || !form.bimestre || !form.ano_serie || !form.disciplina || !form.ae_id) {
      setSkills([]);
      setContents([]);
      return;
    }
    api
      .get("/api/curriculum/conteudos", {
        params: {
          nivel: form.nivel_ensino,
          bimestre: Number(form.bimestre),
          ano: form.ano_serie,
          disciplina: form.disciplina,
          ae_id: Number(form.ae_id),
        },
      })
      .then(({ data }) => setContents(data));
  }, [form.nivel_ensino, form.bimestre, form.ano_serie, form.disciplina, form.ae_id]);

  useEffect(() => {
    if (!form.nivel_ensino || !form.bimestre || !form.ano_serie || !form.disciplina || !form.ae_id) {
      setSkills([]);
      return;
    }
    api
      .get("/api/curriculum/habilidades", {
        params: {
          nivel: form.nivel_ensino,
          bimestre: Number(form.bimestre),
          ano: form.ano_serie,
          disciplina: form.disciplina,
          ae_id: Number(form.ae_id),
        },
      })
      .then(({ data }) => setSkills(data));
  }, [form.nivel_ensino, form.bimestre, form.ano_serie, form.disciplina, form.ae_id]);

  useEffect(() => {
    if (!deferredContents.length) {
      setForm((current) => ({ ...current, habilidades_ids: [] }));
      return;
    }

    setForm((current) => {
      const validSkillIds = new Set(
        skills
          .filter(
            (skill) => deferredContents.includes(skill.objetos_conhecimento) && SELECTABLE_SKILL_CATEGORIES.has(skill.skill_category),
          )
          .map((skill) => skill.id),
      );
      const nextSkillIds = current.habilidades_ids.filter((skillId) => validSkillIds.has(skillId));
      if (nextSkillIds.length === current.habilidades_ids.length) {
        return current;
      }
      return { ...current, habilidades_ids: nextSkillIds };
    });
  }, [deferredContents, skills]);

  const durationOptions = useMemo(() => {
    if (form.nivel_ensino === "Ensino Médio Noturno") {
      return [...NIGHT_DURATIONS, ...DURATIONS];
    }
    return DURATIONS;
  }, [form.nivel_ensino]);

  const skillsByContent = useMemo(() => {
    const groups = new Map(
      contents.map((content) => [
        content.objetos_conhecimento,
        {
          id: content.id,
          objetos_conhecimento: content.objetos_conhecimento,
          unidade_tematica: content.unidade_tematica,
          categories: {
            habilidade_priorizada: [],
            conhecimento_previo: [],
            habilidade_relacionada: [],
          },
        },
      ]),
    );

    skills.forEach((skill) => {
      if (!groups.has(skill.objetos_conhecimento)) {
        groups.set(skill.objetos_conhecimento, {
          id: skill.id,
          objetos_conhecimento: skill.objetos_conhecimento,
          unidade_tematica: null,
          categories: {
            habilidade_priorizada: [],
            conhecimento_previo: [],
            habilidade_relacionada: [],
          },
        });
      }

      const group = groups.get(skill.objetos_conhecimento);
      const category = SKILL_CATEGORY_LABELS[skill.skill_category] ? skill.skill_category : "habilidade_priorizada";
      group.categories[category].push(skill);
    });

    return Array.from(groups.values());
  }, [contents, skills]);

  const selectedSkills = useMemo(
    () => skills.filter((skill) => form.habilidades_ids.includes(skill.id)),
    [form.habilidades_ids, skills],
  );
  const completion = useMemo(
    () => ({
      context: Boolean(
        form.nivel_ensino &&
          form.bimestre &&
          form.ano_serie &&
          form.disciplina &&
          form.ae_id &&
          form.objetivos.trim(),
      ),
      contents: form.conteudos.length > 0,
      skills: form.habilidades_ids.length > 0,
      extras: Boolean(form.orientacoes.trim() || selectedFile || form.duracao),
    }),
    [form, selectedFile],
  );
  const selectedAE = useMemo(() => aes.find((item) => String(item.id) === String(form.ae_id)), [aes, form.ae_id]);
  const stepMeta = {
    context: selectedAE ? `${form.ano_serie} · ${selectedAE.ae_codigo}` : "Defina o recorte",
    contents: form.conteudos.length ? `${form.conteudos.length} conteúdo(s)` : "Selecione os conteúdos",
    skills: form.habilidades_ids.length ? `${form.habilidades_ids.length} habilidade(s)` : "Marque as habilidades",
    extras: selectedFile ? selectedFile.name : form.orientacoes.trim() ? "Orientações adicionadas" : "Instruções complementares",
  };

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function resetAfter(field, value) {
    const base = {
      nivel_ensino: { ...form, nivel_ensino: value, bimestre: "", ano_serie: "", disciplina: "", ae_id: "", conteudos: [], habilidades_ids: [], duracao: "50 minutos" },
      bimestre: { ...form, bimestre: value, ano_serie: "", disciplina: "", ae_id: "", conteudos: [], habilidades_ids: [] },
      ano_serie: { ...form, ano_serie: value, disciplina: "", ae_id: "", conteudos: [], habilidades_ids: [] },
      disciplina: { ...form, disciplina: value, ae_id: "", conteudos: [], habilidades_ids: [] },
      ae_id: { ...form, ae_id: value, conteudos: [], habilidades_ids: [] },
    };
    startTransition(() => {
      setForm(base[field]);
    });
  }

  function toggleArrayValue(field, value) {
    setForm((current) => {
      const exists = current[field].includes(value);
      return {
        ...current,
        [field]: exists ? current[field].filter((item) => item !== value) : [...current[field], value],
      };
    });
  }

  function toggleContentSelection(contentName) {
    setForm((current) => {
      const exists = current.conteudos.includes(contentName);
      const nextContents = exists ? current.conteudos.filter((item) => item !== contentName) : [...current.conteudos, contentName];
      const contentSkillIds = new Set(
        skills
          .filter((skill) => skill.objetos_conhecimento === contentName && SELECTABLE_SKILL_CATEGORIES.has(skill.skill_category))
          .map((skill) => skill.id),
      );

      return {
        ...current,
        conteudos: nextContents,
        habilidades_ids: exists ? current.habilidades_ids.filter((skillId) => !contentSkillIds.has(skillId)) : current.habilidades_ids,
      };
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const payload = {
        ...form,
        bimestre: Number(form.bimestre),
        ae_id: form.ae_id ? Number(form.ae_id) : null,
        material_context: null,
      };

      const selectedExtension = selectedFile ? (selectedFile.name.split(".").pop() || "").toLowerCase() : null;

      if (selectedFile) {
        if (selectedExtension === "pdf") {
          toast.loading("Extraindo texto do PDF...", { id: "pdf-extract" });
          const pdfText = await extractPdfText(selectedFile);
          toast.dismiss("pdf-extract");
          if (pdfText) {
            payload.material_context = pdfText;
            toast.success("Texto do PDF extraído e incluído no contexto.");
          } else {
            payload.material_context = `Material PDF anexado: ${selectedFile.name}. Consulte esse material para orientação do andamento sugerido.`;
            toast.warning("Não foi possível extrair o texto do PDF; o arquivo será referenciado como contexto.");
          }
        } else {
          const textContext = await extractTextFileContext(selectedFile);
          if (textContext) {
            payload.material_context = textContext;
          } else {
            payload.material_context = `Material anexado: ${selectedFile.name}. Use esse material como referência complementar ao elaborar o plano.`;
          }
        }
      }

      const { data } = await api.post("/api/ai/generate", payload);

      const draft = { html: data.html, prompt: data.prompt, metadata: payload, habilidades: skills.filter((skill) => form.habilidades_ids.includes(skill.id)) };
      window.sessionStorage.setItem("redocencia-draft-plan", JSON.stringify(draft));
      toast.success("Plano gerado com sucesso. Abrindo editor...");
      navigate("/editor");
    } catch (requestError) {
      const apiDetail = requestError.response?.data?.detail;
      const apiText = typeof requestError.response?.data === "string" ? requestError.response.data : null;
      const nextError =
        (typeof apiDetail === "string" && apiDetail) ||
        (apiText && apiText.slice(0, 180)) ||
        requestError.message ||
        "Não foi possível gerar o plano.";
      setError(nextError);
      toast.error(nextError);
    } finally {
      setLoading(false);
    }
  }

  function moveStep(direction) {
    const currentIndex = STEP_ORDER.indexOf(activeStep);
    const nextIndex = direction === "next" ? Math.min(currentIndex + 1, STEP_ORDER.length - 1) : Math.max(currentIndex - 1, 0);
    setActiveStep(STEP_ORDER[nextIndex]);
  }

  const canGoNext =
    (activeStep === "context" && completion.context) ||
    (activeStep === "contents" && completion.contents) ||
    (activeStep === "skills" && completion.skills) ||
    activeStep === "extras";

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 pb-28 pt-8 sm:px-6 lg:px-8">
      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_320px]">
        <Card className="border-white/80 bg-white/92">
          <CardHeader>
            <Badge className="w-fit">Gerador de planos</Badge>
            <CardTitle className="max-w-3xl text-3xl">Monte o recorte da aula com segurança antes de pedir o rascunho à IA.</CardTitle>
            <CardDescription className="max-w-2xl text-sm leading-6">
              O fluxo foi reorganizado para reduzir ruído: primeiro o contexto, depois conteúdos, depois habilidades e por fim instruções complementares.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3">
              {[
                { label: "Contexto", step: "context", meta: stepMeta.context },
                { label: "Conteúdos", step: "contents", meta: stepMeta.contents },
                { label: "Habilidades", step: "skills", meta: stepMeta.skills },
                { label: "Instruções", step: "extras", meta: stepMeta.extras },
              ].map((item, index) => (
                <StepIndicator
                  key={item.step}
                  index={index}
                  label={item.label}
                  meta={item.meta}
                  active={activeStep === item.step}
                  completed={completion[item.step]}
                  onClick={() => setActiveStep(item.step)}
                />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-blue-100 bg-blue-50/80">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Resumo atual</CardTitle>
            <CardDescription>O botão final só libera com AE, objetivos e ao menos uma habilidade selecionada.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm text-slate-700">
            <div className="rounded-2xl border border-white/80 bg-white/80 p-4">
              <p className="font-medium text-slate-900">Recorte</p>
              <p className="mt-1 leading-6">{form.nivel_ensino || "Escolha nível, bimestre, ano e disciplina."}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge>{form.conteudos.length} conteúdo(s)</Badge>
              <Badge variant="secondary">{selectedSkills.length} habilidade(s)</Badge>
              <Badge variant="outline">{selectedFile ? "com anexo" : "sem anexo"}</Badge>
            </div>
            <p className="leading-6 text-muted-foreground">Prefira poucos conteúdos por vez para obter rascunhos mais específicos e mais fáceis de revisar.</p>
          </CardContent>
        </Card>
      </section>

      <form id="generator-form" className="grid gap-5" onSubmit={handleSubmit}>
        <Card className={activeStep === "context" ? "border-blue-200 bg-white" : "border-white/80 bg-white/92"}>
          <CardHeader className="gap-4">
            <SectionHeading eyebrow="Etapa 1" title="Contexto da aula" description="Defina o recorte principal antes de abrir conteúdos e habilidades." />
            {activeStep !== "context" ? (
              <button type="button" onClick={() => setActiveStep("context")} className="w-fit text-sm font-medium text-primary hover:underline">
                Editar etapa
              </button>
            ) : null}
          </CardHeader>
          {activeStep === "context" ? (
            <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="grid gap-2 text-sm font-medium">
                Nível de Ensino
                <select className={fieldClassName} value={form.nivel_ensino} onChange={(event) => resetAfter("nivel_ensino", event.target.value)} required>
                  <option value="">Selecione</option>
                  {levels.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-2 text-sm font-medium">
                Bimestre
                <select className={fieldClassName} value={form.bimestre} onChange={(event) => resetAfter("bimestre", event.target.value)} required>
                  <option value="">Selecione</option>
                  {[1, 2, 3, 4].map((item) => (
                    <option key={item} value={item}>
                      {item}º bimestre
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-2 text-sm font-medium">
                Ano/Série
                <select className={fieldClassName} value={form.ano_serie} onChange={(event) => resetAfter("ano_serie", event.target.value)} required>
                  <option value="">Selecione</option>
                  {years.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-2 text-sm font-medium">
                Disciplina
                <select className={fieldClassName} value={form.disciplina} onChange={(event) => resetAfter("disciplina", event.target.value)} required>
                  <option value="">Selecione</option>
                  {subjects.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-2 text-sm font-medium md:col-span-2 xl:col-span-4">
                Aprendizagem Essencial (AE)
                <select className={fieldClassName} value={form.ae_id} onChange={(event) => resetAfter("ae_id", event.target.value)} required>
                  <option value="">Selecione</option>
                  {aes.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.ae_codigo} - {item.descricao}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-2 text-sm font-medium md:col-span-2 xl:col-span-4">
                Objetivo(s) da aula
                <textarea
                  className="min-h-[130px] rounded-[1.5rem] border border-input bg-white px-4 py-3 text-sm leading-6 text-foreground shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  rows="5"
                  value={form.objetivos}
                  onChange={(event) => updateField("objetivos", event.target.value)}
                  placeholder="Descreva o que os alunos devem alcançar ao final da aula."
                  required
                />
              </label>

              <div className="md:col-span-2 xl:col-span-4 flex justify-end">
                <Button type="button" disabled={!completion.context} onClick={() => setActiveStep("contents")}>
                  Avançar para conteúdos
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          ) : (
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Badge>{form.nivel_ensino || "Nível pendente"}</Badge>
                <Badge variant="outline">{form.bimestre ? `${form.bimestre}º bimestre` : "Bimestre pendente"}</Badge>
                <Badge variant="outline">{form.ano_serie || "Ano pendente"}</Badge>
                <Badge variant="outline">{form.disciplina || "Disciplina pendente"}</Badge>
                <Badge variant="outline">{selectedAE ? selectedAE.ae_codigo : "AE pendente"}</Badge>
              </div>
            </CardContent>
          )}
        </Card>

        <Card className={activeStep === "contents" ? "border-blue-200 bg-white" : "border-white/80 bg-white/92"}>
          <CardHeader className="gap-4">
            <SectionHeading eyebrow="Etapa 2" title="Conteúdos da aula" description="Escolha os objetos de conhecimento que irão sustentar o plano." />
            {activeStep !== "contents" ? (
              <button type="button" onClick={() => setActiveStep("contents")} className="w-fit text-sm font-medium text-primary hover:underline">
                Editar etapa
              </button>
            ) : null}
          </CardHeader>
          {activeStep === "contents" ? (
            <CardContent className="space-y-5">
              {contents.length ? (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {contents.map((content) => {
                    const selected = form.conteudos.includes(content.objetos_conhecimento);
                    return (
                      <label
                        key={content.id}
                        className={[
                          "grid cursor-pointer gap-3 rounded-[1.5rem] border p-4 transition-colors",
                          selected ? "border-blue-200 bg-blue-50" : "border-border bg-slate-50/70 hover:bg-slate-100/70",
                        ].join(" ")}
                      >
                        <div className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            className="mt-1 h-4 w-4 accent-[#1a73e8]"
                            checked={selected}
                            onChange={() => toggleContentSelection(content.objetos_conhecimento)}
                          />
                          <div className="space-y-1">
                            <p className="font-semibold text-slate-950">{content.objetos_conhecimento}</p>
                            {content.unidade_tematica ? <p className="text-sm text-muted-foreground">{content.unidade_tematica}</p> : null}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              ) : (
                <div className="rounded-[1.75rem] border border-dashed border-border bg-slate-50/70 p-6">
                  <p className="text-lg font-semibold text-slate-950">Os conteúdos aparecem aqui depois do contexto curricular.</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">Selecione nível, bimestre, ano, disciplina e AE para liberar esta etapa.</p>
                </div>
              )}

              <div className="flex flex-wrap justify-between gap-3">
                <Button type="button" variant="outline" onClick={() => moveStep("back")}>
                  <ChevronLeft className="h-4 w-4" />
                  Voltar
                </Button>
                <Button type="button" disabled={!completion.contents} onClick={() => setActiveStep("skills")}>
                  Avançar para habilidades
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          ) : (
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {form.conteudos.length ? form.conteudos.slice(0, 5).map((content) => <Badge key={content}>{content}</Badge>) : <p className="text-sm text-muted-foreground">Nenhum conteúdo selecionado.</p>}
                {form.conteudos.length > 5 ? <Badge variant="outline">+{form.conteudos.length - 5} adicionais</Badge> : null}
              </div>
            </CardContent>
          )}
        </Card>

        <Card className={activeStep === "skills" ? "border-blue-200 bg-white" : "border-white/80 bg-white/92"}>
          <CardHeader className="gap-4">
            <SectionHeading eyebrow="Etapa 3" title="Habilidades conectadas" description="As habilidades só ficam disponíveis quando o conteúdo correspondente é selecionado." />
            {activeStep !== "skills" ? (
              <button type="button" onClick={() => setActiveStep("skills")} className="w-fit text-sm font-medium text-primary hover:underline">
                Editar etapa
              </button>
            ) : null}
          </CardHeader>
          {activeStep === "skills" ? (
            <CardContent className="space-y-4">
              {skillsByContent.length ? (
                skillsByContent.map((group) => {
                  const contentSelected = form.conteudos.includes(group.objetos_conhecimento);
                  const categories = SKILL_CATEGORY_ORDER.filter((category) => group.categories[category].length);
                  const selectedCount = group.categories.habilidade_priorizada
                    .concat(group.categories.habilidade_relacionada)
                    .concat(group.categories.conhecimento_previo)
                    .filter((skill) => form.habilidades_ids.includes(skill.id)).length;

                  return (
                    <details
                      key={group.objetos_conhecimento}
                      open={contentSelected}
                      className={[
                        "rounded-[1.75rem] border p-5",
                        contentSelected ? "border-blue-200 bg-blue-50/50" : "border-border bg-slate-50/70",
                      ].join(" ")}
                    >
                      <summary className="cursor-pointer list-none">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-lg font-semibold text-slate-950">{group.objetos_conhecimento}</p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              {contentSelected
                                ? "Conteúdo ativo. Agora você pode marcar habilidades priorizadas, relacionadas e conhecimentos prévios."
                                : "Selecione este conteúdo na etapa anterior para habilitar as marcações."}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant={contentSelected ? "default" : "outline"}>{selectedCount} selecionada(s)</Badge>
                            {group.unidade_tematica ? <Badge variant="outline">{group.unidade_tematica}</Badge> : null}
                          </div>
                        </div>
                      </summary>

                      <div className="mt-5 grid gap-4">
                        {categories.map((category) => (
                          <div key={category} className="rounded-[1.25rem] border border-white/80 bg-white/80 p-4">
                            <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-900">{SKILL_CATEGORY_LABELS[category]}</h3>
                            <div className="mt-3 grid gap-3">
                              {SELECTABLE_SKILL_CATEGORIES.has(category)
                                ? group.categories[category].map((skill) => (
                                    <label key={skill.id} className="flex items-start gap-3 rounded-2xl border border-border bg-slate-50/70 p-3">
                                      <input
                                        type="checkbox"
                                        className="mt-1 h-4 w-4 accent-[#1a73e8]"
                                        checked={form.habilidades_ids.includes(skill.id)}
                                        disabled={!contentSelected}
                                        onChange={() => toggleArrayValue("habilidades_ids", skill.id)}
                                      />
                                      <span className="grid gap-1 text-sm">
                                        <span className="font-semibold text-slate-950">{skill.habilidade_codigo}</span>
                                        <span className="leading-6 text-slate-700">{skill.habilidade_descricao}</span>
                                        {(skill.matriz_descritor || skill.matriz_nivel) ? (
                                          <span className="text-xs text-muted-foreground">
                                            Matriz: {skill.matriz_descritor || "-"} | {skill.matriz_nivel || "-"}
                                          </span>
                                        ) : null}
                                      </span>
                                    </label>
                                  ))
                                : group.categories[category].map((skill) => (
                                    <div key={skill.id} className="rounded-2xl border border-border bg-slate-50/70 p-3 text-sm">
                                      <span className="font-semibold text-slate-950">{skill.habilidade_codigo}</span>
                                      <span className="ml-2 text-slate-700">{skill.habilidade_descricao}</span>
                                    </div>
                                  ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  );
                })
              ) : (
                <div className="rounded-[1.75rem] border border-dashed border-border bg-slate-50/70 p-6">
                  <p className="text-lg font-semibold text-slate-950">As habilidades serão organizadas aqui por conteúdo.</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">Defina o contexto curricular para liberar o agrupamento e manter a seleção consistente.</p>
                </div>
              )}

              <div className="flex flex-wrap justify-between gap-3">
                <Button type="button" variant="outline" onClick={() => moveStep("back")}>
                  <ChevronLeft className="h-4 w-4" />
                  Voltar
                </Button>
                <Button type="button" disabled={!completion.skills} onClick={() => setActiveStep("extras")}>
                  Avançar para instruções
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          ) : (
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {selectedSkills.length ? selectedSkills.slice(0, 6).map((skill) => <Badge key={skill.id}>{skill.habilidade_codigo}</Badge>) : <p className="text-sm text-muted-foreground">Nenhuma habilidade selecionada.</p>}
                {selectedSkills.length > 6 ? <Badge variant="outline">+{selectedSkills.length - 6} adicionais</Badge> : null}
              </div>
            </CardContent>
          )}
        </Card>

        <Card className={activeStep === "extras" ? "border-blue-200 bg-white" : "border-white/80 bg-white/92"}>
          <CardHeader className="gap-4">
            <SectionHeading eyebrow="Etapa 4" title="Instruções e contexto extra" description="Refine o prompt com informações metodológicas e materiais de apoio." />
            {activeStep !== "extras" ? (
              <button type="button" onClick={() => setActiveStep("extras")} className="w-fit text-sm font-medium text-primary hover:underline">
                Editar etapa
              </button>
            ) : null}
          </CardHeader>
          {activeStep === "extras" ? (
            <CardContent className="space-y-6">
              <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                <div className="space-y-4">
                  <div className="space-y-3">
                    <p className="text-sm font-medium text-slate-900">Duração da aula</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {durationOptions.map((item) => (
                        <button
                          key={item}
                          type="button"
                          onClick={() => updateField("duracao", item)}
                          className={[
                            "flex items-center justify-between rounded-[1.35rem] border px-4 py-3 text-left text-sm font-medium transition-colors",
                            form.duracao === item ? "border-blue-200 bg-blue-50 text-primary" : "border-border bg-slate-50/70 text-slate-800 hover:bg-slate-100/70",
                          ].join(" ")}
                        >
                          <span>{item}</span>
                          {form.duracao === item ? <Check className="h-4 w-4" /> : null}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-[1.5rem] border border-border bg-slate-50/70 p-4">
                    <label className="grid gap-3 text-sm font-medium">
                      Material de apoio
                      <div className="rounded-[1.25rem] border border-dashed border-border bg-white p-4">
                        <div className="flex items-center gap-3 text-sm text-slate-700">
                          <Paperclip className="h-4 w-4 text-primary" />
                          <span>{selectedFile ? `Arquivo selecionado: ${selectedFile.name}` : "Anexe PDF, TXT, DOC ou DOCX para enriquecer a geração."}</span>
                        </div>
                        <input className="mt-3 block w-full text-sm text-muted-foreground file:mr-4 file:rounded-full file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-[#1557b0]" type="file" accept=".pdf,.txt,.doc,.docx" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} />
                      </div>
                    </label>
                  </div>
                </div>

                <label className="grid gap-2 text-sm font-medium">
                  Orientações adicionais
                  <textarea
                    className="min-h-[220px] rounded-[1.5rem] border border-input bg-white px-4 py-3 text-sm leading-6 text-foreground shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    rows="8"
                    value={form.orientacoes}
                    onChange={(event) => updateField("orientacoes", event.target.value)}
                    placeholder="Ex.: foco em recuperação contínua, avaliação formativa, atividade prática, adaptação para TEA ou integração com laboratório."
                  />
                </label>
              </div>

              {selectedSkills.length ? (
                <div className="space-y-3 rounded-[1.5rem] border border-border bg-slate-50/70 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                    <Target className="h-4 w-4 text-primary" />
                    Habilidades selecionadas
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedSkills.slice(0, 8).map((skill) => (
                      <Badge key={skill.id}>{skill.habilidade_codigo}</Badge>
                    ))}
                    {selectedSkills.length > 8 ? <Badge variant="outline">+{selectedSkills.length - 8} adicionais</Badge> : null}
                  </div>
                </div>
              ) : null}

              {error ? <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

              <div className="flex flex-wrap justify-between gap-3">
                <Button type="button" variant="outline" onClick={() => moveStep("back")}>
                  <ChevronLeft className="h-4 w-4" />
                  Voltar
                </Button>
                <Button type="submit" disabled={loading || !form.habilidades_ids.length || !completion.context}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                  {loading ? "Gerando plano..." : "Gerar plano de aula"}
                </Button>
              </div>
            </CardContent>
          ) : (
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Badge>{form.duracao}</Badge>
                {selectedFile ? <Badge variant="outline">{selectedFile.name}</Badge> : null}
                {form.orientacoes.trim() ? <Badge variant="secondary">com orientações</Badge> : null}
              </div>
            </CardContent>
          )}
        </Card>
      </form>

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border/80 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <Badge>{form.conteudos.length} conteúdo(s)</Badge>
            <Badge variant="secondary">{form.habilidades_ids.length} habilidade(s)</Badge>
            <Badge variant="outline">{selectedFile ? "material anexado" : "sem anexo"}</Badge>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="outline" disabled={activeStep === "context"} onClick={() => moveStep("back")}>
              <ChevronLeft className="h-4 w-4" />
              Anterior
            </Button>
            <Button type="button" variant="outline" disabled={!canGoNext || activeStep === "extras"} onClick={() => moveStep("next")}>
              Próxima etapa
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button type="submit" form="generator-form" disabled={loading || !form.habilidades_ids.length || !completion.context}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading ? "Gerando..." : "Gerar plano"}
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}
