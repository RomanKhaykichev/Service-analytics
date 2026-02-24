import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { ChartPreviewBlock } from "@/components/landing/ChartPreviewBlock";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Testimonials } from "@/components/landing/Testimonials";
import { FAQ } from "@/components/landing/FAQ";
import { CtaGreenBlock } from "@/components/landing/CtaGreenBlock";
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
        <ChartPreviewBlock />
        <Features />
        <HowItWorks />
        <Testimonials />
        <FAQ />
        <CtaGreenBlock />
      </main>
      <Footer />
    </div>
  );
}
