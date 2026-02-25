import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLanguage, type Language } from "@/contexts/LanguageContext";
import { Container } from "./Container";

const navItems = [
  { label: "Возможности", href: "#features" },
  { label: "Как это работает", href: "#how-it-works" },
  { label: "Отзывы", href: "#testimonials" },
  { label: "Вопросы", href: "#faq" },
];

/** Зелёный треугольник логотипа PROFiboard */
function LogoIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="flex-shrink-0">
      <path d="M10 2L18 18H2L10 2Z" fill="currentColor" className="text-green-500" />
    </svg>
  );
}

const languages: { code: Language; label: string }[] = [
  { code: "ru", label: "Русский" },
  { code: "uz", label: "O'zbekcha" },
];

interface HeaderProps {
  onOpenAuth?: (tab: 'signin' | 'signup') => void;
}

/** Шапка лендинга. TODO: сверить логотип, отступы и пункты меню с Figma. */
export function Header({ onOpenAuth }: HeaderProps) {
  const [open, setOpen] = useState(false);
  const { language, setLanguage } = useLanguage();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-[#c4ffdf]">
      <Container className="flex h-14 sm:h-16 items-center justify-between gap-4">
        <Link
          to="/landing"
          className="flex items-center gap-2 text-foreground"
          onClick={() => setOpen(false)}
        >
          <LogoIcon />
          <span className="text-lg"><span className="font-bold">PROFi</span><span className="font-normal">board</span></span>
        </Link>

        <nav className="hidden md:flex items-center gap-6">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="shrink-0" aria-label="Язык">
                <Globe className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {languages.map(({ code, label }) => (
                <DropdownMenuItem
                  key={code}
                  onClick={() => setLanguage(code)}
                  className={language === code ? "bg-primary/5" : undefined}
                >
                  {label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          {onOpenAuth ? (
            <>
              <Button variant="ghost" size="sm" className="hidden sm:inline-flex" onClick={() => onOpenAuth('signin')}>
                Войти
              </Button>
              <Button size="sm" onClick={() => onOpenAuth('signup')}>
                Начать
              </Button>
            </>
          ) : (
            <>
              <Link to="/auth" className="hidden sm:inline-flex">
                <Button variant="ghost" size="sm">
                  Войти
                </Button>
              </Link>
              <Link to="/auth">
                <Button size="sm">Начать</Button>
              </Link>
            </>
          )}

          <button
            type="button"
            className="md:hidden p-2 rounded-md hover:bg-muted"
            onClick={() => setOpen(!open)}
            aria-label="Меню"
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </Container>

      {open && (
        <div className="md:hidden border-t border-border/50 bg-background">
          <Container className="py-4 flex flex-col gap-3">
            {navItems.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-sm text-muted-foreground hover:text-foreground py-2"
                onClick={() => setOpen(false)}
              >
                {item.label}
              </a>
            ))}
            {onOpenAuth ? (
              <Button variant="outline" className="w-full mt-2" onClick={() => { setOpen(false); onOpenAuth('signin'); }}>
                Войти
              </Button>
            ) : (
              <Link to="/auth" className="pt-2" onClick={() => setOpen(false)}>
                <Button variant="outline" className="w-full">
                  Войти
                </Button>
              </Link>
            )}
          </Container>
        </div>
      )}
    </header>
  );
}
