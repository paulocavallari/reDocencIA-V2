import { BookOpen, Home, LogOut, Menu, Settings, Sparkles } from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { Avatar, AvatarFallback } from "./ui/avatar";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Separator } from "./ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "./ui/sheet";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Painel", icon: Home },
  { to: "/gerador", label: "Novo plano", icon: Sparkles },
  { to: "/planos", label: "Biblioteca", icon: BookOpen },
];

function getInitials(name) {
  if (!name) {
    return "RD";
  }

  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export default function Navbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 border-b border-border/40 bg-white/80 backdrop-blur-2xl backdrop-saturate-150">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" className="flex min-w-0 items-center gap-2.5">
            <img src="/logo1.png" alt="redocêncIA" className="h-8 w-8 rounded-lg" />
            <span className="text-[15px] font-semibold tracking-tight text-foreground">redocêncIA</span>
          </Link>

          <nav className="hidden items-center gap-1 lg:flex">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.to === "/"}>
                {({ isActive }) => (
                  <span
                    className={[
                      "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-[15px] font-medium transition-colors",
                      isActive ? "text-primary" : "text-muted-foreground hover:text-foreground",
                    ].join(" ")}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </span>
                )}
              </NavLink>
            ))}
            {user?.is_admin ? (
              <NavLink to="/admin">
                {({ isActive }) => (
                  <span
                    className={[
                      "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-[15px] font-medium transition-colors",
                      isActive ? "text-primary" : "text-muted-foreground hover:text-foreground",
                    ].join(" ")}
                  >
                    <Settings className="h-4 w-4" />
                    Admin
                  </span>
                )}
              </NavLink>
            ) : null}
          </nav>

          <div className="hidden items-center gap-2 lg:flex">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="inline-flex items-center gap-2.5 rounded-xl p-1.5 text-left transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
                  <Avatar>
                    <AvatarFallback>{getInitials(user?.nome)}</AvatarFallback>
                  </Avatar>
                  <span className="hidden min-w-0 pr-1 xl:block">
                    <span className="block truncate text-[13px] font-semibold text-foreground">{user?.nome || "Usuário"}</span>
                    <span className="block truncate text-[11px] text-muted-foreground">{user?.is_admin ? "Admin" : "Professor(a)"}</span>
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="space-y-0.5">
                    <p className="text-[15px] font-semibold text-foreground">{user?.nome || "Usuário"}</p>
                    <p className="text-[12px] font-normal text-muted-foreground">{user?.is_admin ? "Administrador" : "Professor(a)"}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {user?.is_admin ? (
                  <DropdownMenuItem onSelect={() => navigate("/admin")}>
                    <Settings className="h-4 w-4" />
                    Administração
                  </DropdownMenuItem>
                ) : null}
                <DropdownMenuItem onSelect={handleLogout} className="text-destructive focus:text-destructive">
                  <LogOut className="h-4 w-4" />
                  Sair
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div className="lg:hidden">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="Abrir navegação">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="max-w-xs">
                <SheetHeader>
                  <SheetTitle>Navegação</SheetTitle>
                  <SheetDescription>Acesse as áreas da plataforma.</SheetDescription>
                </SheetHeader>

                <div className="mt-5 flex items-center gap-3 rounded-xl bg-secondary p-3">
                  <Avatar>
                    <AvatarFallback>{getInitials(user?.nome)}</AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <p className="truncate text-[15px] font-semibold text-foreground">{user?.nome || "Usuário"}</p>
                    <p className="truncate text-[13px] text-muted-foreground">{user?.is_admin ? "Admin" : "Professor(a)"}</p>
                  </div>
                </div>

                <Separator className="my-4" />

                <nav className="grid gap-1">
                  {NAV_ITEMS.map((item) => (
                    <NavLink key={item.to} to={item.to} end={item.to === "/"}>
                      {({ isActive }) => (
                        <span
                          className={[
                            "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition-colors",
                            isActive ? "bg-primary/8 text-primary" : "text-foreground hover:bg-secondary",
                          ].join(" ")}
                        >
                          <item.icon className="h-4 w-4" />
                          {item.label}
                        </span>
                      )}
                    </NavLink>
                  ))}
                  {user?.is_admin ? (
                    <NavLink to="/admin">
                      {({ isActive }) => (
                        <span
                          className={[
                            "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition-colors",
                            isActive ? "bg-primary/8 text-primary" : "text-foreground hover:bg-secondary",
                          ].join(" ")}
                        >
                          <Settings className="h-4 w-4" />
                          Administração
                        </span>
                      )}
                    </NavLink>
                  ) : null}
                </nav>

                <Button variant="ghost" className="mt-auto w-full justify-start text-destructive hover:text-destructive" onClick={handleLogout}>
                  <LogOut className="h-4 w-4" />
                  Sair
                </Button>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>
      <div className="h-14" aria-hidden="true" />
    </>
  );
}
