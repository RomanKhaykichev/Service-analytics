import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Testimonials } from "@/components/landing/Testimonials";
import { FAQ } from "@/components/landing/FAQ";
import { CtaPlovBlock } from "@/components/landing/CtaPlovBlock";
import { Footer } from "@/components/landing/Footer";

/**
 * Лендинг (маркетинговая страница).
 * Структура сверстана по типовому макету; точные тексты, отступы и ассеты — см. TODO в компонентах (Figma).
 */
export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <main className="flex-1">
        <Hero />
        <Features />
        <HowItWorks />
        <Testimonials />
        <FAQ />
        <CtaPlovBlock />
      </main>
      <Footer />
    </div>
  );
}
