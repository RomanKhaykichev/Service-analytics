import { Link } from "react-router-dom";
import { Container } from "./Container";
import { Send } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const legalLinksRu = [
  { label: "Политика конфиденциальности", href: "/privacy" },
  { label: "Публичная оферта", href: "/offer" },
];

const legalLinksUz = [
  { label: "Maxfiylik siyosati", href: "/privacy" },
  { label: "Ommaviy oferta", href: "/offer" },
];

/** Подвал лендинга по макету: лого PROFiboard, соцсети, контакты слева; юридические ссылки справа. */
export function Footer() {
  const { language } = useLanguage();
  const legalLinks = language === "uz" ? legalLinksUz : legalLinksRu;
  const contactsLabel = language === "uz" ? "Aloqa:" : "Контакты:";

  return (
    <footer id="contacts" className="bg-zinc-100 py-10 sm:py-12 scroll-mt-20">
      <Container>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          {/* Слева: лого, соцсети, контакты */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 font-normal text-foreground text-lg">
                <img src="/favicon.png" alt="" className="h-5 w-5 flex-shrink-0 object-contain" />
                <span><span className="font-bold">PROFi</span>board</span>
              </span>
              <span className="flex items-center gap-1.5 ml-1">
                <a
                  href="https://t.me/PROFI_BOARD"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-300 text-white hover:bg-zinc-400 transition-colors"
                  aria-label="Telegram @PROFI_BOARD"
                >
                  <Send className="h-4 w-4" />
                </a>
              </span>
            </div>
            <p className="text-sm text-zinc-500">
              {contactsLabel} supportprofiboard@gmail.com
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
