import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Container } from "./Container";

/** Hero-секция. TODO: тексты и иллюстрация — один в один из Figma frame 1. */
export function Hero() {
  return (
    <section className="relative overflow-hidden bg-white py-16 sm:py-20 md:py-24 lg:py-28">
      <Container className="relative flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
        <div className="flex-1 text-center lg:text-left max-w-2xl">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight">
            Аналитика для вашего бизнеса
          </h1>
          <p className="mt-4 sm:mt-6 text-lg text-muted-foreground">
            Управляйте продажами, финансами и складом в одном месте. Отчёты, тренды и рекомендации на основе данных.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
            <Link to="/auth">
              <Button size="xl" variant="hero">
                Попробовать бесплатно
              </Button>
            </Link>
            <a href="#how-it-works">
              <Button size="xl" variant="outline">
                Как это работает
              </Button>
            </a>
          </div>
        </div>
        <div className="flex-1 flex justify-center lg:justify-end w-full max-w-lg">
          {/* TODO: заменить на hero-illustration из Figma — src/assets/landing/hero-illustration.svg или .png */}
          <div
            className="w-full aspect-square max-w-md rounded-2xl bg-primary/10 flex items-center justify-center text-primary/50"
            aria-hidden
          >
            <span className="text-sm">Hero illustration</span>
          </div>
        </div>
      </Container>
    </section>
  );
}
