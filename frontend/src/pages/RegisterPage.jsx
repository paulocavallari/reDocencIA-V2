import { useEffect, useState } from "react";
import { Loader2, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useAuth } from "../context/AuthContext";
import { isSupabaseConfigured } from "../services/supabase";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, user } = useAuth();
  const [form, setForm] = useState({ nome: "", email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      navigate("/", { replace: true });
    }
  }, [navigate, user]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccessMessage("");
    setSubmitting(true);
    try {
      const result = await register(form);
      if (result?.pendingConfirmation) {
        const pendingMessage = `Cadastro criado para ${result.email}. Confirme o email enviado pelo Supabase.`;
        setSuccessMessage(pendingMessage);
        toast.success("Cadastro criado. Verifique seu email.");
        return;
      }
      navigate("/");
    } catch (requestError) {
      const nextError = requestError.response?.data?.detail || requestError.message || "Não foi possível concluir o cadastro.";
      setError(nextError);
      toast.error(nextError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page-shell">
      <div className="relative z-10 grid min-h-screen lg:grid-cols-[minmax(0,1.1fr)_minmax(460px,0.9fr)]">
        <section className="auth-gradient-panel relative hidden overflow-hidden px-10 py-12 text-white lg:flex lg:flex-col lg:justify-between">
          <div className="relative z-10 space-y-10">
            <div className="flex items-center gap-3">
              <img src="/logo1.png" alt="redocêncIA" className="h-10 w-10 rounded-xl" />
              <span className="text-[13px] font-medium uppercase tracking-[0.2em] text-white/60">Novo acesso</span>
            </div>

            <div className="max-w-lg space-y-4">
              <h1 className="text-[40px] font-bold leading-[1.1] tracking-tight">
                Crie sua conta e entre no fluxo de planejamento.
              </h1>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                {
                  icon: UserRound,
                  title: "Biblioteca individual",
                  description: "Cada professor mantém seus planos e histórico em um espaço próprio.",
                },
                {
                  icon: Sparkles,
                  title: "Entrada rápida",
                  description: "Poucos campos e acesso direto ao painel assim que a conta estiver pronta.",
                },
                {
                  icon: ShieldCheck,
                  title: "Confirmação segura",
                  description: "Quando o Supabase estiver ativo, o email pode ser validado antes do login.",
                },
              ].map((item) => (
                <article key={item.title} className="rounded-2xl bg-white/10 p-5">
                  <item.icon className="mb-3 h-5 w-5 text-white/70" />
                  <h2 className="text-[15px] font-semibold">{item.title}</h2>
                  <p className="mt-2 text-[13px] leading-5 text-white/60">{item.description}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="relative z-10 text-[13px] text-white/50">
            Geração assistida, editor autoral e exportação no mesmo ambiente.
          </div>
        </section>

        <section className="flex min-h-screen items-center justify-center px-5 py-10">
          <div className="w-full max-w-md space-y-6">
            <div className="flex items-center gap-2.5 lg:hidden">
              <img src="/logo1.png" alt="redocêncIA" className="h-8 w-8 rounded-lg" />
              <div>
                <p className="text-[15px] font-semibold text-foreground">redocêncIA</p>
                <p className="text-[13px] text-muted-foreground">Novo acesso</p>
              </div>
            </div>

            <div className="space-y-2">
              <h1 className="text-[34px] font-bold tracking-tight text-foreground">Criar conta</h1>
              <p className="text-[15px] leading-relaxed text-muted-foreground">
                {isSupabaseConfigured
                  ? "Sua conta será criada no Supabase Auth e pode exigir confirmação por email."
                  : "Crie sua conta local e siga direto para o primeiro plano de aula."}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="nome">Nome</Label>
                <Input id="nome" value={form.nome} onChange={(event) => setForm((current) => ({ ...current, nome: event.target.value }))} placeholder="Seu nome completo" required />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                  placeholder="seu@email.com"
                  required
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="username">Usuário</Label>
                  <Input
                    id="username"
                    value={form.username}
                    onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                    placeholder="nome_usuario"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="password">Senha</Label>
                  <Input
                    id="password"
                    type="password"
                    value={form.password}
                    onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>

              {successMessage ? <p className="rounded-xl bg-[hsl(var(--success))]/8 px-4 py-3 text-[13px] text-[hsl(var(--success))]">{successMessage}</p> : null}
              {error ? <p className="rounded-xl bg-destructive/8 px-4 py-3 text-[13px] text-destructive">{error}</p> : null}

              <Button type="submit" className="w-full" size="lg" disabled={submitting}>
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {submitting ? "Salvando..." : "Criar conta"}
              </Button>
            </form>

            <p className="text-center text-[13px] text-muted-foreground">
              Já tem conta?{" "}
              <Link to="/login" className="font-semibold text-primary">
                Entrar
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
