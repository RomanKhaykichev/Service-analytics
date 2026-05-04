import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/** Прокрутка: в начало при смене пути; если в URL есть якорь — к элементу (не перебиваем #features и т.п.). */
export function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (hash) {
      const id = decodeURIComponent(hash.slice(1));
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "auto", block: "start" });
        return;
      }
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);

  return null;
}
