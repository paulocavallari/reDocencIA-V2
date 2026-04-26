import { useEffect, useState } from "react";
import { Database, FileSpreadsheet, KeyRound, RefreshCcw, ShieldCheck, Wand2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import api from "../services/api";
import { getSupabaseConfig } from "../services/supabase";

const DEFAULT_OPENROUTER_MODELS = [
  "liquid/lfm-2.5-1.2b-thinking:free",
  "liquid/lfm-2.5-1.2b-instruct:free",
  "inclusionai/ling-2.6-flash:free",
];

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState(null);
  const [dbStatus, setDbStatus] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState(["", "", ""]);
  const [guideFile, setGuideFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState(false);
  const [savingModels, setSavingModels] = useState(false);
  const [uploadingGuide, setUploadingGuide] = useState(false);
  const supabaseConfig = getSupabaseConfig();
  const importState = settings?.curriculum_import;
  const dbEngineLabel =
    dbStatus?.engine === "postgres"
      ? dbStatus?.is_supabase
        ? "Supabase Postgres"
        : "PostgreSQL"
      : dbStatus?.engine === "sqlite"
        ? "SQLite"
        : "carregando";
  async function loadPageData() {
    setLoading(true);
    const [{ data: settingsData }, { data: dbData }] = await Promise.all([
      api.get("/api/admin/settings"),
      api.get("/api/admin/db-status"),
    ]);
    setSettings(settingsData);
    setDbStatus(dbData);
    const configuredModels = Array.isArray(settingsData.openrouter_models)
      ? settingsData.openrouter_models
      : [settingsData.openrouter_model || ""];
    const normalizedModels = [
      (configuredModels?.[0] || "").trim(),
      (configuredModels?.[1] || "").trim(),
      (configuredModels?.[2] || "").trim(),
    ];
    setModels(normalizedModels.map((model, index) => model || DEFAULT_OPENROUTER_MODELS[index]));
    setLoading(false);
  }

  useEffect(() => {
    loadPageData();
  }, []);

  async function saveApiKey() {
    setSavingKey(true);
    try {
      await api.put("/api/admin/settings/api-key", { value: apiKey });
      toast.success("Chave OpenRouter salva.");
      setApiKey("");
      await loadPageData();
    } catch {
      toast.error("Não foi possível salvar a chave OpenRouter.");
    } finally {
      setSavingKey(false);
    }
  }

  async function saveModels() {
    setSavingModels(true);
    try {
      await api.put("/api/admin/settings/models", { values: models });
      toast.success("Modelos OpenRouter salvos.");
      await loadPageData();
    } catch {
      toast.error("Não foi possível salvar os modelos.");
    } finally {
      setSavingModels(false);
    }
  }

  async function uploadGuide() {
    if (!guideFile) {
      return;
    }
    setUploadingGuide(true);
    const formData = new FormData();
    formData.append("file", guideFile);
    try {
      const { data } = await api.post("/api/admin/upload-guide", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`${data.message} ${data.records} registros processados.`);
      setGuideFile(null);
      await loadPageData();
    } catch {
      toast.error("Não foi possível atualizar o guia curricular.");
    } finally {
      setUploadingGuide(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 pb-12 pt-8 sm:px-6 lg:px-8">
      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.05fr)_340px]">
        <Card className="border-white/80 bg-white/92">
          <CardHeader>
            <Badge className="w-fit">Administração</Badge>
            <CardTitle className="text-3xl">Ambiente, integrações e currículo</CardTitle>
            <CardDescription>Centralize aqui a configuração do modelo, do provedor de autenticação e da base curricular usada pelo gerador.</CardDescription>
          </CardHeader>
        </Card>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1">
          <Card className="border-white/80 bg-white/92">
            <CardHeader className="pb-3">
              <CardDescription>Registros curriculares</CardDescription>
              <CardTitle className="text-4xl">{settings?.curriculum_records || 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="border-white/80 bg-white/92">
            <CardHeader className="pb-3">
              <CardDescription>Guias detectados</CardDescription>
              <CardTitle className="text-4xl">{settings?.guide_files?.length || 0}</CardTitle>
            </CardHeader>
          </Card>
        </div>
      </section>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Visão geral</TabsTrigger>
          <TabsTrigger value="openrouter">OpenRouter</TabsTrigger>
          <TabsTrigger value="supabase">Supabase</TabsTrigger>
          <TabsTrigger value="curriculum">Currículo</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              {
                icon: KeyRound,
                title: "OpenRouter",
                value: settings?.openrouter_api_key || "não configurado",
                text: "Chave atualmente registrada para geração dos planos.",
              },
              {
                icon: ShieldCheck,
                title: "Supabase",
                value: supabaseConfig.configured ? "ativo" : "pendente",
                text: supabaseConfig.projectRef || "Projeto não identificado",
              },
              {
                icon: Database,
                title: "Banco de dados",
                value: dbEngineLabel,
                text: dbStatus ? `${dbStatus.host} · pool ${dbStatus.pool_mode} · SSL ${dbStatus.ssl} · conexão ${dbStatus.connection_ok ? "ok" : "falhou"}` : "Lendo status do backend.",
              },
              {
                icon: RefreshCcw,
                title: "Importação",
                value: importState ? importState.status : "sem dados",
                text: importState ? `${importState.processed_guides}/${importState.total_guides} guias processados` : "Aguardando leitura do backend.",
              },
            ].map((item) => (
              <Card key={item.title} className="border-white/80 bg-white/92">
                <CardHeader className="pb-3">
                  <CardDescription className="flex items-center gap-2">
                    <item.icon className="h-4 w-4" />
                    {item.title}
                  </CardDescription>
                  <CardTitle className="text-2xl leading-tight">{item.value}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-6 text-muted-foreground">{item.text}</p>
                </CardContent>
              </Card>
            ))}
          </section>
        </TabsContent>

        <TabsContent value="openrouter">
          <section className="grid gap-4 lg:grid-cols-2">
            <Card className="border-white/80 bg-white/92">
              <CardHeader>
                <CardTitle>Chave de API</CardTitle>
                <CardDescription>Valor atual: {settings?.openrouter_api_key || "não configurado"}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Cole a chave aqui" />
                <Button type="button" onClick={saveApiKey} disabled={savingKey || !apiKey.trim()}>
                  {savingKey ? "Salvando..." : "Salvar chave"}
                </Button>
              </CardContent>
            </Card>

            <Card className="border-white/80 bg-white/92">
              <CardHeader>
                <CardTitle>Modelos com fallback</CardTitle>
                <CardDescription>Defina até 3 modelos em ordem: mais rápido, fallback 1 e fallback 2.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  value={models[0]}
                  onChange={(event) => setModels((current) => [event.target.value, current[1], current[2]])}
                  placeholder="1º (mais rápido) ex.: liquid/lfm-2.5-1.2b-thinking:free"
                />
                <Input
                  value={models[1]}
                  onChange={(event) => setModels((current) => [current[0], event.target.value, current[2]])}
                  placeholder="2º (fallback) ex.: liquid/lfm-2.5-1.2b-instruct:free"
                />
                <Input
                  value={models[2]}
                  onChange={(event) => setModels((current) => [current[0], current[1], event.target.value])}
                  placeholder="3º (fallback) ex.: inclusionai/ling-2.6-flash:free"
                />
                <Button type="button" onClick={saveModels} disabled={savingModels || !models.some((item) => item.trim())}>
                  {savingModels ? "Salvando..." : "Salvar modelos"}
                </Button>
              </CardContent>
            </Card>
          </section>
        </TabsContent>

        <TabsContent value="supabase">
          <Card className="border-white/80 bg-white/92">
            <CardHeader>
              <CardTitle>Conexão do frontend</CardTitle>
              <CardDescription>Resumo da configuração ativa do cliente Supabase.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              {[
                ["Status", supabaseConfig.configured ? "cliente inicializado" : "pendente de configuração"],
                ["Projeto", supabaseConfig.projectRef || "não identificado"],
                ["URL", supabaseConfig.url || "não configurada"],
                ["Chave pública", supabaseConfig.keyPreview],
              ].map(([label, value]) => (
                <div key={label} className="rounded-[1.5rem] border bg-slate-50/70 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
                  <p className="mt-2 break-all text-sm font-medium text-slate-900">{value}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="curriculum">
          <section className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_380px]">
            <Card className="border-white/80 bg-white/92">
              <CardHeader>
                <CardTitle>Estado da base curricular</CardTitle>
                <CardDescription>
                  Último guia enviado: {settings?.guide_path || "nenhum upload manual"} · registros no banco: {settings?.curriculum_records || 0}
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4">
                <div className="rounded-[1.5rem] border bg-slate-50/70 p-4">
                  <p className="text-sm font-semibold text-slate-900">Importação</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    {importState ? `Status: ${importState.status} · ${importState.processed_guides}/${importState.total_guides} guias processados` : "Aguardando leitura do backend."}
                    {importState?.last_error ? ` · erro: ${importState.last_error}` : ""}
                  </p>
                </div>

                <div className="rounded-[1.5rem] border bg-slate-50/70 p-4">
                  <p className="text-sm font-semibold text-slate-900">Disciplinas carregadas</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(settings?.curriculum_disciplines || []).length ? (settings.curriculum_disciplines || []).map((discipline) => <Badge key={discipline}>{discipline}</Badge>) : <p className="text-sm text-muted-foreground">Nenhuma disciplina listada.</p>}
                  </div>
                </div>

                <div className="rounded-[1.5rem] border bg-slate-50/70 p-4">
                  <p className="text-sm font-semibold text-slate-900">Guias detectados</p>
                  <div className="mt-3 grid gap-2">
                    {(settings?.guide_files || []).length ? (settings.guide_files || []).map((file) => <div key={file} className="rounded-2xl border bg-white p-3 text-sm text-slate-700">{file}</div>) : <p className="text-sm text-muted-foreground">Nenhum guia detectado.</p>}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/80 bg-white/92">
              <CardHeader>
                <CardTitle>Atualizar guia</CardTitle>
                <CardDescription>Envie um novo PDF para reprocessar a base curricular.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-[1.5rem] border border-dashed bg-slate-50/70 p-4 text-sm text-muted-foreground">
                  <p>{guideFile ? `Arquivo selecionado: ${guideFile.name}` : "Selecione um PDF do Guia do Currículo Priorizado."}</p>
                  <input className="mt-3 block w-full text-sm file:mr-4 file:rounded-full file:border-0 file:bg-primary file:px-4 file:py-2 file:font-semibold file:text-white hover:file:bg-[#1557b0]" type="file" accept=".pdf" onChange={(event) => setGuideFile(event.target.files?.[0] || null)} />
                </div>
                <Button type="button" onClick={uploadGuide} disabled={uploadingGuide || !guideFile}>
                  {uploadingGuide ? "Atualizando..." : "Atualizar guia"}
                </Button>
              </CardContent>
            </Card>
          </section>
        </TabsContent>
      </Tabs>

      {loading ? <div className="hidden" aria-hidden="true" /> : null}
    </main>
  );
}
