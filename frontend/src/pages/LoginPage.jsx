import { useState } from "react";
import { Loader2, LockKeyhole, Mail, MoveRight, Shapes, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useAuth } from "../context/AuthContext";
import { isSupabaseConfigured } from "../services/supabase";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ identifier: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(form.identifier, form.password);
      navigate("/");
    } catch (requestError) {
      const nextError = requestError.response?.data?.detail || requestError.message || "Não foi possível entrar.";
      setError(nextError);
      toast.error(nextError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page-shell">
      <div className="relative z-10 grid min-h-screen lg:grid-cols-[minmax(0,1.15fr)_minmax(460px,0.85fr)]">
        <section className="auth-gradient-panel relative hidden overflow-hidden px-8 py-10 text-white lg:flex lg:flex-col lg:justify-between xl:px-12">
          <div className="relative z-10 space-y-8">
            <div className="flex items-center gap-4">
              <img src="/logo1.png" alt="redocêncIA" className="h-14 w-14 rounded-2xl bg-white/10 p-2" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-white/70">Ambiente de planejamento</p>
                <h1 className="mt-2 max-w-md text-4xl font-semibold tracking-tight">Planejamento pedagógico claro, rápido e realmente utilizável.</h1>
              </div>
            </div>

            <p className="max-w-xl text-base leading-7 text-white/78">
              Organize o recorte curricular, gere o primeiro rascunho com IA e refine o resultado em um fluxo pensado para o trabalho docente.
            </p>

            <div className="grid gap-4 xl:grid-cols-3">
              {[
                {
                  icon: Shapes,
                  title: "Recorte guiado",
                  description: "Seleções em cascata reduzem erro e aceleram a montagem do contexto da aula.",
                },
                {
                  icon: Sparkles,
                  title: "IA com direção",
                  description: "O rascunho nasce estruturado e continua aberto para revisão autoral.",
                },
                {
                  icon: MoveRight,
                  title: "Fluxo contínuo",
                  description: "Gerar, editar, salvar e exportar sem trocar de ambiente.",
                },
              ].map((item) => (
                <article key={item.title} className="rounded-[1.75rem] border border-white/15 bg-white/10 p-5 backdrop-blur-sm">
                  <item.icon className="mb-4 h-5 w-5 text-white/80" />
                  <h2 className="text-lg font-semibold">{item.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-white/72">{item.description}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="relative z-10 rounded-[1.75rem] border border-white/15 bg-white/10 p-5 backdrop-blur-sm">
            <p className="text-sm font-medium text-white/70">Orientação da plataforma</p>
            <p className="mt-2 text-lg font-semibold">Funcional primeiro. Resultado bonito depois. Clareza sempre.</p>
          </div>
        </section>

        <section className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6 lg:px-10">
          <div className="w-full max-w-md space-y-6">
            <div className="flex items-center justify-center gap-3 lg:hidden">
              <img src="/logo1.png" alt="redocêncIA" className="h-12 w-12 rounded-2xl border border-border bg-white p-2 shadow-sm" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.26em] text-muted-foreground">redocêncIA</p>
                <p className="text-sm text-muted-foreground">Planejamento com IA para a rede estadual</p>
              </div>
            </div>

            <Card className="border-white/80 bg-white/90">
              <CardHeader className="space-y-3 pb-6">
                <div className="inline-flex w-fit items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-primary">
                  Acesso
                </div>
                <CardTitle className="text-3xl">Entrar</CardTitle>
                <CardDescription className="text-sm leading-6">
                  {isSupabaseConfigured ? "Entre com email ou usuário para continuar o planejamento." : "Use o usuário admin/admin ou faça seu cadastro para começar."}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="identifier">{isSupabaseConfigured ? "Email ou usuário" : "Usuário"}</Label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="identifier"
                        type="text"
                        value={form.identifier}
                        onChange={(event) => setForm((current) => ({ ...current, identifier: event.target.value }))}
                        placeholder={isSupabaseConfigured ? "nome@dominio.com ou usuario" : "Digite seu usuário"}
                        className="pl-11"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Senha</Label>
                    <div className="relative">
                      <LockKeyhole className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="password"
                        type="password"
                        value={form.password}
                        onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                        className="pl-11"
                        required
                      />
                    </div>
                  </div>

                  {error ? <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

                  <Button type="submit" className="w-full" size="lg" disabled={submitting}>
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {submitting ? "Entrando..." : "Entrar"}
                  </Button>
                </form>

                <div className="mt-6 rounded-3xl border border-blue-100 bg-blue-50/60 p-4 text-sm text-slate-700">
                  <p className="font-medium text-slate-900">Acesso mais rápido</p>
                  <p className="mt-1 leading-6">Depois do login você segue direto para o painel com atalhos para gerar, editar e salvar planos.</p>
                </div>

                <p className="mt-6 text-center text-sm text-muted-foreground">
                  Ainda não tem conta?{" "}
                  <Link to="/cadastro" className="font-semibold text-primary hover:underline">
                    Criar cadastro
                  </Link>
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}
