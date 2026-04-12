import { Link } from "react-router-dom";
import { Container } from "@/components/landing/Container";
import { cn } from "@/lib/utils";

export type LegalBlock =
  | { type: "p"; text: string }
  | { type: "row"; cells: string[] };

function blockVariant(
  text: string,
  index: number
): "title" | "subtitle" | "h2" | "h3" | "body" {
  if (index === 0) return "title";
  if (index === 1) return "subtitle";
  if (/^\d+\.\d/.test(text)) {
    return text.length < 180 ? "h3" : "body";
  }
  if (/^[1-9]\d*\.\s/.test(text) && text.length < 100) {
    return "h2";
  }
  return "body";
}

interface LegalDocumentViewProps {
  blocks: LegalBlock[];
  backHref?: string;
  backLabel?: string;
}

export function LegalDocumentView({
  blocks,
  backHref = "/landing",
  backLabel = "На главную",
}: LegalDocumentViewProps) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <Container className="py-4 flex items-center justify-between gap-4">
          <Link
            to={backHref}
            className="flex items-center gap-1.5 text-lg text-foreground"
          >
            <img
              src="/favicon.png"
              alt=""
              className="h-5 w-5 object-contain"
            />
            <span>
              <span className="font-bold">PROFi</span>board
            </span>
          </Link>
          <Link
            to={backHref}
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            ← {backLabel}
          </Link>
        </Container>
      </header>
      <main className="flex-1 py-10 sm:py-14">
        <Container>
          <article className="mx-auto max-w-3xl">
            {blocks.map((block, i) => {
              if (block.type === "row") {
                return (
                  <div
                    key={`row-${i}`}
                    className="my-4 grid gap-2 text-sm sm:text-base border border-border rounded-lg p-3 bg-muted/30"
                    style={{
                      gridTemplateColumns: `repeat(${block.cells.length}, minmax(0, 1fr))`,
                    }}
                  >
                    {block.cells.map((cell, j) => (
                      <p key={j} className="leading-relaxed break-words">
                        {cell}
                      </p>
                    ))}
                  </div>
                );
              }
              const v = blockVariant(block.text, i);
              return (
                <p
                  key={i}
                  className={cn(
                    v === "title" &&
                      "text-3xl sm:text-4xl font-bold tracking-tight text-foreground mb-2",
                    v === "subtitle" &&
                      "text-sm sm:text-base text-muted-foreground mb-8 sm:mb-10",
                    v === "h2" &&
                      "text-xl font-bold text-foreground mt-10 mb-3 scroll-mt-24",
                    (v === "h3" || v === "body") &&
                      "text-sm sm:text-base text-foreground/90 font-normal leading-relaxed mb-4 last:mb-0"
                  )}
                >
                  {block.text}
                </p>
              );
            })}
          </article>
        </Container>
      </main>
    </div>
  );
}
