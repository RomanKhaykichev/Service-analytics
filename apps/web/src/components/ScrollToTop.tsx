import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/** Прокрутка окна в начало при смене пути (в т.ч. юридические страницы). */
export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}
