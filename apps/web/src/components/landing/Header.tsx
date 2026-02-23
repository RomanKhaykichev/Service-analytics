import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Container } from "./Container";

const navItems = [
  { label: "Возможности", href: "#features" },
  { label: "Как это работает", href: "#how-it-works" },
  { label: "Отзывы", href: "#testimonials" },
  { label: "Вопросы", href: "#faq" },
];

/** Шапка лендинга. TODO: сверить логотип, отступы и пункты меню с Figma. */
export function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <Container className="flex h-14 sm:h-16 items-center justify-between gap-4">
        <Link
          to="/landing"
          className="flex items-center gap-2 font-semibold text-foreground"
          onClick={() => setOpen(false)}
        >
          {/* TODO: заменить на лого из Figma — src/assets/landing/logo.svg */}
          <span className="text-lg">Service Analytics</span>
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
          <Link to="/auth" className="hidden sm:inline-flex">
            <Button variant="ghost" size="sm">
              Войти
            </Button>
          </Link>
          <Link to="/auth">
            <Button size="sm">Начать</Button>
          </Link>

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
            <Link to="/auth" className="pt-2" onClick={() => setOpen(false)}>
              <Button variant="outline" className="w-full">
                Войти
              </Button>
            </Link>
          </Container>
        </div>
      )}
    </header>
  );
}
