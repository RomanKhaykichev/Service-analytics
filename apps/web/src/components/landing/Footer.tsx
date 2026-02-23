import { Link } from "react-router-dom";
import { Container } from "./Container";

const footerLinks = [
  { label: "Возможности", href: "#features" },
  { label: "Вопросы", href: "#faq" },
  { label: "Войти", href: "/auth" },
];

/** Подвал лендинга. TODO: ссылки и копирайт — из Figma. */
export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-white py-10 sm:py-12">
      <Container>
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            Service Analytics
          </div>
          <nav className="flex flex-wrap items-center justify-center gap-6">
            {footerLinks.map((link) =>
              link.href.startsWith("#") ? (
                <a
                  key={link.href}
                  href={link.href}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {link.label}
                </a>
              ) : (
                <Link
                  key={link.href}
                  to={link.href}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {link.label}
                </Link>
              )
            )}
          </nav>
        </div>
        <p className="mt-8 text-center text-sm text-muted-foreground">
          © {year} Service Analytics. Все права защищены.
        </p>
      </Container>
    </footer>
  );
}
