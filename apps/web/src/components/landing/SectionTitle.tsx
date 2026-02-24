import { cn } from "@/lib/utils";

interface SectionTitleProps {
  title: string;
  subtitle?: string;
  className?: string;
  titleClassName?: string;
  subtitleClassName?: string;
}

/** Заголовок секции лендинга. TODO: сверить размеры и отступы с Figma. */
export function SectionTitle({
  title,
  subtitle,
  className,
  titleClassName,
  subtitleClassName,
}: SectionTitleProps) {
  return (
    <div className={cn("text-center mb-10 md:mb-12 lg:mb-14", className)}>
      <h2
        className={cn(
          "text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight",
          titleClassName
        )}
      >
        {title}
      </h2>
      {subtitle && (
        <p
          className={cn(
            "mt-3 sm:mt-4 text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto",
            subtitleClassName
          )}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}
