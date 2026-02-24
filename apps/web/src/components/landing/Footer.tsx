import { Link } from "react-router-dom";
import { Container } from "./Container";
import { Send, Camera } from "lucide-react";

/** Зелёный треугольник логотипа PROFiboard */
function LogoIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="flex-shrink-0">
      <path d="M10 2L18 18H2L10 2Z" fill="currentColor" className="text-green-500" />
    </svg>
  );
}

const legalLinks = [
  { label: "Политика конфиденциальности", href: "/privacy" },
  { label: "Публичная оферта", href: "/offer" },
  { label: "Пользовательское соглашение", href: "/terms" },
];

/** Подвал лендинга по макету: лого PROFiboard, соцсети, контакты слева; юридические ссылки справа. */
export function Footer() {
  return (
    <footer className="bg-zinc-100 py-10 sm:py-12">
      <Container>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          {/* Слева: лого, соцсети, контакты */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 font-normal text-foreground text-lg">
                <LogoIcon />
                <span><span className="font-bold">PROFi</span>board</span>
              </span>
              <span className="flex items-center gap-1.5 ml-1">
                <a
                  href="https://t.me/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-300 text-white hover:bg-zinc-400 transition-colors"
                  aria-label="Telegram"
                >
                  <Send className="h-4 w-4" />
                </a>
                <a
                  href="https://instagram.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-300 text-white hover:bg-zinc-400 transition-colors"
                  aria-label="Instagram"
                >
                  <Camera className="h-4 w-4" />
                </a>
              </span>
            </div>
            <p className="text-sm text-zinc-500">
              Контакты: +0000000000 00000@gmail.com
            </p>
          </div>
          {/* Справа: юридические ссылки */}
          <nav className="flex flex-wrap items-center gap-6 md:gap-8">
            {legalLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className="text-sm text-zinc-500 hover:text-zinc-700 transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </Container>
    </footer>
  );
}
